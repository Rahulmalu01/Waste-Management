import json
from datetime import timedelta, datetime, date
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Sum, Count, Q

from .models import (
    Bin, BinReading, DeviceAuthLog,
    UserPoints, Achievement, UserAchievement, ActivityLog, UserStreak, Leaderboard
)
from .forms import BinForm

from alerts.models import Alert
from alerts.services import (
    create_bin_full_alert,
    resolve_bin_full_alert,
    create_bin_offline_alert,
    resolve_bin_offline_alert,
)


# ============================================
# UTILITY FUNCTIONS
# ============================================

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


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============================================
# BIN LISTING & DASHBOARD VIEWS
# ============================================

@login_required
def bin_list_view(request):
    update_offline_bins()
    bins = Bin.objects.all().order_by('-updated_at')
    return render(request, 'bin_list.html', {'bins': bins})


def bin_dashboard_view(request):
    if request.user.role not in ['ADMIN', 'MANAGER']:
        return redirect('role_redirect')
    
    bins = Bin.objects.all()
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
    return render(request, 'dashboard.html', context)


def bin_map_view(request):
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
    return render(request, 'bin_map.html', {'bins': bin_data})


# ============================================
# SENSOR DATA INGESTION API
# ============================================

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
        
        if not all([bin_id, device_key, distance_cm is not None, latitude is not None, longitude is not None]):
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
        
        DeviceAuthLog.objects.create(
            bin=bin_obj,
            status='SUCCESS',
            raw_payload=data,
            ip_address=get_client_ip(request)
        )
        
        return JsonResponse({
            'message': 'Bin data stored successfully.',
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


# ============================================
# INCENTIVE SYSTEM HELPERS
# ============================================

def add_activity_points(request, activity_type, points=0, description="", bin_id=None):
    try:
        user_points = UserPoints.objects.get(user=request.user)
    except UserPoints.DoesNotExist:
        user_points = UserPoints.objects.create(user=request.user)
    
    activity = ActivityLog.objects.create(
        user=request.user,
        activity_type=activity_type,
        points_earned=points,
        description=description,
        related_bin_id=bin_id
    )
    
    user_points.total_points += points
    user_points.lifetime_points += points
    user_points.last_activity_date = date.today()
    user_points.update_tier()
    user_points.update_level()
    user_points.save()
    
    try:
        streak = UserStreak.objects.get(user=request.user)
        today = date.today()
        last_date = streak.current_streak_date
        
        if last_date == today:
            pass
        elif (today - last_date).days == 1:
            streak.streak_count += 1
            if streak.streak_count > streak.best_streak_count:
                streak.best_streak_count = streak.streak_count
        else:
            streak.last_broken_date = last_date
            streak.streak_count = 1
        
        streak.total_active_days += 1
        streak.current_streak_date = today
        streak.save()
    except UserStreak.DoesNotExist:
        UserStreak.objects.create(user=request.user, streak_count=1, total_active_days=1)
    
    return activity


def check_and_award_achievements(request):
    user = request.user
    earned_achievements = UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
    available_achievements = Achievement.objects.filter(
        is_active=True
    ).exclude(id__in=earned_achievements)
    
    for achievement in available_achievements:
        if achievement.category == 'CONSISTENCY':
            try:
                streak = UserStreak.objects.get(user=user)
                if streak.streak_count >= achievement.condition_value:
                    UserAchievement.objects.create(
                        user=user,
                        achievement=achievement
                    )
                    add_activity_points(request, 'CONSISTENCY_BONUS', achievement.points_reward)
            except:
                pass
        
        elif achievement.category == 'REPORTING':
            report_count = ActivityLog.objects.filter(
                user=user,
                activity_type__in=['BIN_REPORT', 'BIN_CLEARED']
            ).count()
            
            if report_count >= achievement.condition_value:
                UserAchievement.objects.create(
                    user=user,
                    achievement=achievement
                )
                add_activity_points(request, 'CONSISTENCY_BONUS', achievement.points_reward)
    
    return True


# ============================================
# INCENTIVE SYSTEM VIEWS
# ============================================

@login_required
def user_points_view(request):
    user_points, created = UserPoints.objects.get_or_create(user=request.user)
    recent_activities = ActivityLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    earned_achievements = UserAchievement.objects.filter(user=request.user)
    
    context = {
        'user_points': user_points,
        'recent_activities': recent_activities,
        'earned_achievements': earned_achievements,
    }
    return render(request, 'incentives/user_points.html', context)


@login_required
def leaderboard_view(request):
    period = request.GET.get('period', 'all')
    
    if period == 'monthly':
        current_month = date.today().replace(day=1)
        rankings = UserPoints.objects.filter(last_activity_date__gte=current_month).order_by('-total_points')[:50]
    elif period == 'weekly':
        last_week = date.today() - timedelta(days=7)
        rankings = UserPoints.objects.filter(last_activity_date__gte=last_week).order_by('-total_points')[:50]
    else:
        rankings = UserPoints.objects.all().order_by('-lifetime_points')[:50]
    
    context = {
        'rankings': rankings,
        'period': period,
    }
    return render(request, 'incentives/leaderboard.html', context)


@login_required
def achievements_view(request):
    all_achievements = Achievement.objects.filter(is_active=True).order_by('category', 'name')
    earned_achievement_ids = UserAchievement.objects.filter(user=request.user).values_list('achievement_id', flat=True)
    
    earned = all_achievements.filter(id__in=earned_achievement_ids)
    available = all_achievements.exclude(id__in=earned_achievement_ids)
    
    categories = Achievement.CATEGORY_CHOICES
    achievements_by_category = {}
    for code, label in categories:
        achievements_by_category[label] = {
            'earned': earned.filter(category=code),
            'available': available.filter(category=code),
        }
    
    context = {
        'achievements_by_category': achievements_by_category,
        'total_earned': earned.count(),
        'total_available': available.count(),
        'total_achievements': all_achievements.count(),
    }
    return render(request, 'incentives/achievements.html', context)


@login_required
def activity_log_view(request):
    activities = ActivityLog.objects.filter(user=request.user).order_by('-created_at')
    
    paginator = Paginator(activities, 20)
    page = request.GET.get('page', 1)
    page_activities = paginator.get_page(page)
    
    today_activities = ActivityLog.objects.filter(
        user=request.user,
        created_at__date=date.today()
    ).count()
    
    today_points = ActivityLog.objects.filter(
        user=request.user,
        created_at__date=date.today()
    ).aggregate(Sum('points_earned'))['points_earned__sum'] or 0
    
    context = {
        'page_activities': page_activities,
        'paginator': paginator,
        'today_activities': today_activities,
        'today_points': today_points,
    }
    return render(request, 'incentives/activity_log.html', context)


# ============================================
# BIN MANAGEMENT VIEWS (DRIVER/MANAGER)
# ============================================

@login_required
def bin_management_list(request):
    if request.user.role not in ['DRIVER', 'MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    bins = Bin.objects.all().order_by('-updated_at')
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        bins = bins.filter(
            models.Q(bin_id__icontains=search) |
            models.Q(name__icontains=search) |
            models.Q(location_name__icontains=search)
        )
    
    if status_filter:
        bins = bins.filter(status=status_filter)
    
    paginator = Paginator(bins, 10)
    page = request.GET.get('page', 1)
    page_bins = paginator.get_page(page)
    
    total_bins = Bin.objects.count()
    full_bins = Bin.objects.filter(status='FULL').count()
    empty_bins = Bin.objects.filter(status='EMPTY').count()
    offline_bins = Bin.objects.filter(status='OFFLINE').count()
    
    context = {
        'page_bins': page_bins,
        'paginator': paginator,
        'total_bins': total_bins,
        'full_bins': full_bins,
        'empty_bins': empty_bins,
        'offline_bins': offline_bins,
        'search': search,
        'status_filter': status_filter,
    }
    return render(request, 'bins/bin_management_list.html', context)


@login_required
def bin_create(request):
    if request.user.role not in ['MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    if request.method == 'POST':
        form = BinForm(request.POST)
        if form.is_valid():
            bin_obj = form.save()
            add_activity_points(
                request,
                activity_type='COMMUNITY_ACTION',
                points=20,
                description=f'Added new bin: {bin_obj.name}'
            )
            check_and_award_achievements(request)
            return redirect('bin_management_list')
    else:
        form = BinForm()
    
    return render(request, 'bins/bin_form.html', {
        'form': form,
        'title': 'Add New Bin',
        'action': 'Create',
    })


@login_required
def bin_update(request, bin_id):
    if request.user.role not in ['MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    bin_obj = get_object_or_404(Bin, id=bin_id)
    
    if request.method == 'POST':
        form = BinForm(request.POST, instance=bin_obj)
        if form.is_valid():
            bin_obj = form.save()
            add_activity_points(
                request,
                activity_type='COMMUNITY_ACTION',
                points=10,
                description=f'Updated bin: {bin_obj.name}'
            )
            check_and_award_achievements(request)
            return redirect('bin_management_list')
    else:
        form = BinForm(instance=bin_obj)
    
    return render(request, 'bins/bin_form.html', {
        'form': form,
        'bin': bin_obj,
        'title': 'Edit Bin',
        'action': 'Update',
    })


@login_required
def bin_delete(request, bin_id):
    if request.user.role not in ['MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    bin_obj = get_object_or_404(Bin, id=bin_id)
    
    if request.method == 'POST':
        bin_name = bin_obj.name
        bin_obj.delete()
        add_activity_points(
            request,
            activity_type='COMMUNITY_ACTION',
            points=5,
            description=f'Removed bin: {bin_name}'
        )
        check_and_award_achievements(request)
        return redirect('bin_management_list')
    
    return render(request, 'bins/bin_confirm_delete.html', {'bin': bin_obj})


@login_required
def bin_detail(request, bin_id):
    if request.user.role not in ['DRIVER', 'MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    bin_obj = get_object_or_404(Bin, id=bin_id)
    recent_readings = bin_obj.readings.all().order_by('-created_at')[:20]
    
    last_7_days = timezone.now() - timedelta(days=7)
    chart_readings = bin_obj.readings.filter(created_at__gte=last_7_days).order_by('created_at')
    
    fill_data = [r.fill_percentage for r in chart_readings]
    dates = [r.created_at.strftime('%H:%M') for r in chart_readings]
    
    context = {
        'bin': bin_obj,
        'recent_readings': recent_readings,
        'fill_data': fill_data,
        'dates': dates,
        'chart_data': {
            'labels': dates,
            'data': fill_data,
        }
    }
    return render(request, 'bins/bin_detail.html', context)


@login_required
def bin_toggle_status(request, bin_id):
    if request.user.role not in ['MANAGER', 'ADMIN']:
        return redirect('role_redirect')
    
    bin_obj = get_object_or_404(Bin, id=bin_id)
    bin_obj.is_active = not bin_obj.is_active
    bin_obj.save()
    
    status_text = "activated" if bin_obj.is_active else "deactivated"
    add_activity_points(
        request,
        activity_type='COMMUNITY_ACTION',
        points=5,
        description=f'{status_text.capitalize()} bin: {bin_obj.name}'
    )
    
    return redirect('bin_detail', bin_id=bin_obj.id)


# Legacy sensor data endpoint (alternate API format)
@csrf_exempt
@require_POST
def ingest_sensor_data(request):
    """Legacy endpoint - delegates to main API"""
    return ingest_bin_data(request)
