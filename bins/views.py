import json
from datetime import timedelta, datetime, date

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import (
    Bin, BinReading, DeviceAuthLog,
    UserPoints, Achievement, UserAchievement, ActivityLog, UserStreak, Leaderboard
)

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
    return render(request, 'bin_list.html', {'bins': bins})

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
    return render(request, 'dashboard.html', context)

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
    return render(request, 'bin_map.html', {'bins': bin_data})

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
        fill_percentage = (1 - (distance / bin_obj.bin_height_cm)) * 100
        fill_percentage = max(0, min(100, fill_percentage))
        bin_obj.current_distance_cm = distance
        bin_obj.fill_percentage = fill_percentage
        bin_obj.latitude = latitude or bin_obj.latitude
        bin_obj.longitude = longitude or bin_obj.longitude
        if fill_percentage >= 80:
            bin_obj.status = "FULL"
        elif fill_percentage >= 40:
            bin_obj.status = "PARTIAL"
        else:
            bin_obj.status = "EMPTY"
        bin_obj.save()
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

# ============================================
# INCENTIVE SYSTEM VIEWS
# ============================================

from django.db.models import Sum, Count, Q
from datetime import datetime, date

@login_required
def user_points_view(request):
    """Display user points and rewards dashboard"""
    from .models import UserPoints, ActivityLog, UserAchievement
    
    # Get or create user points profile
    user_points, created = UserPoints.objects.get_or_create(user=request.user)
    
    # Get recent activities
    recent_activities = ActivityLog.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Get user achievements
    achievements = UserAchievement.objects.filter(
        user=request.user
    ).select_related('achievement').order_by('-earned_at')
    
    # Calculate stats
    total_reports = ActivityLog.objects.filter(
        user=request.user, 
        activity_type__in=['BIN_REPORT', 'BIN_CLEARED']
    ).count()
    
    week_points = ActivityLog.objects.filter(
        user=request.user,
        created_at__gte=timezone.now() - timedelta(days=7)
    ).aggregate(Sum('points_earned'))['points_earned__sum'] or 0
    
    context = {
        'user_points': user_points,
        'recent_activities': recent_activities,
        'achievements': achievements,
        'total_reports': total_reports,
        'week_points': week_points,
    }
    return render(request, 'incentives/user_points.html', context)


@login_required
def leaderboard_view(request):
    """Display leaderboard rankings"""
    from .models import Leaderboard, UserPoints
    
    period = request.GET.get('period', 'MONTHLY')
    
    # Get leaderboard for the selected period
    leaderboard_entries = Leaderboard.objects.filter(
        period=period
    ).select_related('user').order_by('rank')[:50]
    
    # Get current user's rank
    user_rank = Leaderboard.objects.filter(
        user=request.user,
        period=period
    ).first()
    
    # Fallback: Get top users by total points if leaderboard data doesn't exist
    if not leaderboard_entries:
        top_users = UserPoints.objects.all().order_by('-total_points')[:50]
        leaderboard_entries = top_users
    
    context = {
        'leaderboard': leaderboard_entries,
        'selected_period': period,
        'user_rank': user_rank,
        'periods': ['WEEKLY', 'MONTHLY', 'ALLTIME']
    }
    return render(request, 'incentives/leaderboard.html', context)


@login_required
def achievements_view(request):
    """Display all achievements"""
    from .models import Achievement, UserAchievement
    
    # Get all available achievements
    all_achievements = Achievement.objects.filter(is_active=True).order_by('category', 'name')
    
    # Get user's earned achievements
    earned_achievement_ids = UserAchievement.objects.filter(
        user=request.user
    ).values_list('achievement_id', flat=True)
    
    # Separate earned and available
    earned = all_achievements.filter(id__in=earned_achievement_ids)
    available = all_achievements.exclude(id__in=earned_achievement_ids)
    
    # Group by category
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
    """Display user activity log"""
    from .models import ActivityLog
    
    # Get activities with pagination
    from django.core.paginator import Paginator
    
    activities = ActivityLog.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    paginator = Paginator(activities, 20)
    page = request.GET.get('page', 1)
    page_activities = paginator.get_page(page)
    
    # Activity stats
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


@login_required
def add_activity_points(request, activity_type, points=0, description="", bin_id=None):
    """Helper function to add activity and update user points"""
    from .models import ActivityLog, UserPoints, UserStreak
    from datetime import date
    
    try:
        user_points = UserPoints.objects.get(user=request.user)
    except UserPoints.DoesNotExist:
        user_points = UserPoints.objects.create(user=request.user)
    
    # Create activity log
    activity = ActivityLog.objects.create(
        user=request.user,
        activity_type=activity_type,
        points_earned=points,
        description=description,
        related_bin_id=bin_id
    )
    
    # Update user points
    user_points.total_points += points
    user_points.lifetime_points += points
    user_points.last_activity_date = date.today()
    user_points.update_tier()
    user_points.update_level()
    user_points.save()
    
    # Update streak
    try:
        streak = UserStreak.objects.get(user=request.user)
        today = date.today()
        last_date = streak.current_streak_date
        
        if last_date == today:
            # Already logged today, no change
            pass
        elif (today - last_date).days == 1:
            # Consecutive day, increment streak
            streak.streak_count += 1
            if streak.streak_count > streak.best_streak_count:
                streak.best_streak_count = streak.streak_count
        else:
            # Streak broken
            streak.last_broken_date = last_date
            streak.streak_count = 1
        
        streak.total_active_days += 1
        streak.save()
    except UserStreak.DoesNotExist:
        UserStreak.objects.create(user=request.user, streak_count=1, total_active_days=1)
    
    return activity


@login_required
def check_and_award_achievements(request):
    """Check if user qualifies for any achievements and award them"""
    from .models import Achievement, UserAchievement, ActivityLog, UserAchievement
    
    user = request.user
    earned_achievements = UserAchievement.objects.filter(user=user).values_list('achievement_id', flat=True)
    available_achievements = Achievement.objects.filter(
        is_active=True
    ).exclude(id__in=earned_achievements)
    
    for achievement in available_achievements:
        if achievement.category == 'CONSISTENCY':
            # Check daily visit streak
            try:
                streak = user.streak_info
                if streak.streak_count >= achievement.condition_value:
                    UserAchievement.objects.create(
                        user=user,
                        achievement=achievement
                    )
                    add_activity_points(request, 'CONSISTENCY_BONUS', achievement.points_reward)
            except:
                pass
        
        elif achievement.category == 'REPORTING':
            # Check total reports
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


