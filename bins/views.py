import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Bin, BinReading, DeviceAuthLog
from alerts.models import Alert
from alerts.services import (
    create_bin_full_alert,
    resolve_bin_full_alert,
    create_bin_offline_alert,
    resolve_bin_offline_alert,
)

def update_offline_bins():
    threshold_minutes = getattr(settings, 'OFFLINE_THRESHOLD_MINUTES', 15)
    cutoff_time = timezone.now() - timedelta(minutes=threshold_minutes)

    bins_to_mark_offline = Bin.objects.filter(
        is_active=True,
        last_seen__isnull=False,
        last_seen__lt=cutoff_time
    ).exclude(status='OFFLINE')

    for bin_obj in bins_to_mark_offline:
        bin_obj.status = 'OFFLINE'
        bin_obj.save(update_fields=['status', 'updated_at'])
        create_bin_offline_alert(bin_obj)


@login_required
def bin_list_view(request):
    update_offline_bins()
    bins = Bin.objects.all().order_by('-updated_at')
    return render(request, 'bins/bin_list.html', {'bins': bins})


@login_required
def bin_dashboard_view(request):
    if request.user.role not in ['ADMIN', 'MANAGER']:
        return redirect('role_redirect')

    update_offline_bins()
    bins = Bin.objects.all().order_by('-updated_at')

    context = {
        'bins': bins,
        'total_bins': Bin.objects.count(),
        'full_bins': Bin.objects.filter(status='FULL').count(),
        'partial_bins': Bin.objects.filter(status='PARTIAL').count(),
        'offline_bins': Bin.objects.filter(status='OFFLINE').count(),
        'empty_bins': Bin.objects.filter(status='EMPTY').count(),
        'active_alerts': Alert.objects.filter(status='ACTIVE').count(),
        'resolved_alerts': Alert.objects.filter(status='RESOLVED').count(),
    }
    return render(request, 'bins/dashboard.html', context)


@login_required
def bin_map_view(request):
    if request.user.role not in ['ADMIN', 'MANAGER']:
        return redirect('role_redirect')

    update_offline_bins()
    bins = Bin.objects.all()

    bin_data = []
    for bin_obj in bins:
        bin_data.append({
            'bin_id': bin_obj.bin_id,
            'name': bin_obj.name,
            'location_name': bin_obj.location_name,
            'latitude': bin_obj.latitude,
            'longitude': bin_obj.longitude,
            'fill_percentage': bin_obj.fill_percentage,
            'status': bin_obj.status,
            'last_seen': bin_obj.last_seen.strftime('%Y-%m-%d %H:%M:%S') if bin_obj.last_seen else None,
        })

    return render(request, 'bins/bin_map.html', {'bins': bin_data})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@csrf_exempt
@require_POST
def ingest_bin_data(request):
    try:
        data = json.loads(request.body)

        bin_id = data.get('bin_id')
        device_key = data.get('device_key')
        distance_cm = data.get('distance_cm')
        latitude = data.get('latitude')
        longitude = data.get('longitude')

        if not all([
            bin_id,
            device_key,
            distance_cm is not None,
            latitude is not None,
            longitude is not None,
        ]):
            DeviceAuthLog.objects.create(
                bin_id_attempted=bin_id,
                provided_device_key=device_key,
                ip_address=get_client_ip(request),
                status='MISSING_FIELDS',
                raw_payload=data
            )
            return JsonResponse({'error': 'Missing required fields.'}, status=400)

        try:
            distance_cm = float(distance_cm)
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            DeviceAuthLog.objects.create(
                bin_id_attempted=bin_id,
                provided_device_key=device_key,
                ip_address=get_client_ip(request),
                status='INVALID_NUMERIC_VALUES',
                raw_payload=data
            )
            return JsonResponse({'error': 'Invalid numeric values.'}, status=400)

        try:
            bin_obj = Bin.objects.get(
                bin_id=bin_id,
                device_key=device_key,
                is_active=True
            )
        except Bin.DoesNotExist:
            DeviceAuthLog.objects.create(
                bin_id_attempted=bin_id,
                provided_device_key=device_key,
                ip_address=get_client_ip(request),
                status='UNAUTHORIZED_OR_INACTIVE_DEVICE',
                raw_payload=data
            )
            return JsonResponse({'error': 'Unauthorized or inactive device.'}, status=401)

        fill_percentage = bin_obj.calculate_fill_percentage(distance_cm)

        bin_obj.current_distance_cm = distance_cm
        bin_obj.fill_percentage = fill_percentage
        bin_obj.latitude = latitude
        bin_obj.longitude = longitude
        bin_obj.last_seen = timezone.now()
        bin_obj.update_status()
        bin_obj.save()

        # Device is back online if it sends data again
        resolve_bin_offline_alert(bin_obj)

        BinReading.objects.create(
            bin=bin_obj,
            distance_cm=distance_cm,
            fill_percentage=fill_percentage,
            latitude=latitude,
            longitude=longitude,
            raw_payload=data
        )

        alert_created = False

        if bin_obj.status == 'FULL':
            _, created = create_bin_full_alert(bin_obj)
            alert_created = created
        else:
            resolve_bin_full_alert(bin_obj)

        return JsonResponse({
            'message': 'Bin data stored successfully.',
            'bin_id': bin_obj.bin_id,
            'fill_percentage': bin_obj.fill_percentage,
            'status': bin_obj.status,
            'alert_created': alert_created,
        }, status=200)

    except json.JSONDecodeError:
        DeviceAuthLog.objects.create(
            ip_address=get_client_ip(request),
            status='INVALID_JSON',
            raw_payload=None
        )
        return JsonResponse({'error': 'Invalid JSON format.'}, status=400)

    except Exception as e:
        DeviceAuthLog.objects.create(
            ip_address=get_client_ip(request),
            status='SERVER_ERROR',
            raw_payload={'error': str(e)}
        )
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def ingest_sensor_data(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)

        device_id = data.get("device_id")
        distance = data.get("distance")  # cm
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        if not device_id:
            return JsonResponse({"error": "device_id required"}, status=400)

        try:
            bin_obj = Bin.objects.get(device_id=device_id)
        except Bin.DoesNotExist:
            return JsonResponse({"error": "Bin not registered."}, status=404)

        # calculate fill %
        fill_percentage = (1 - (distance / bin_obj.bin_height_cm)) * 100
        fill_percentage = max(0, min(100, fill_percentage))

        # update bin
        bin_obj.current_distance_cm = distance
        bin_obj.fill_percentage = fill_percentage
        bin_obj.latitude = latitude or bin_obj.latitude
        bin_obj.longitude = longitude or bin_obj.longitude

        # update status
        if fill_percentage >= 80:
            bin_obj.status = "FULL"
        elif fill_percentage >= 40:
            bin_obj.status = "PARTIAL"
        else:
            bin_obj.status = "EMPTY"

        bin_obj.save()

        # save reading
        BinReading.objects.create(
            bin=bin_obj,
            distance_cm=distance,
            fill_percentage=fill_percentage,
            latitude=latitude,
            longitude=longitude,
        )

        return JsonResponse({
            "message": "Data stored",
            "fill_percentage": fill_percentage
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)