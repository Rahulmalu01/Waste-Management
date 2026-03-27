from django.contrib import admin
from .models import (
    Bin, BinReading, DeviceAuthLog,
    UserPoints, Achievement, UserAchievement, ActivityLog, UserStreak, Leaderboard
)

@admin.register(Bin)
class BinAdmin(admin.ModelAdmin):
    list_display = (
        'bin_id',
        'name',
        'location_name',
        'fill_percentage',
        'status',
        'device_key',
        'last_seen',
        'is_active',
    )
    search_fields = ('bin_id', 'name', 'location_name', 'device_key')
    list_filter = ('status', 'is_active')
    readonly_fields = ('device_key',)

@admin.register(BinReading)
class BinReadingAdmin(admin.ModelAdmin):
    list_display = ('bin', 'distance_cm', 'fill_percentage', 'created_at')
    search_fields = ('bin__bin_id', 'bin__name')
    list_filter = ('created_at',)

@admin.register(DeviceAuthLog)
class DeviceAuthLogAdmin(admin.ModelAdmin):
    list_display = ('bin_id_attempted', 'status', 'ip_address', 'created_at')
    search_fields = ('bin_id_attempted', 'provided_device_key', 'status')
    list_filter = ('status', 'created_at')

# ============================================
# INCENTIVE SYSTEM ADMIN
# ============================================

@admin.register(UserPoints)
class UserPointsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_points', 'level', 'tier', 'current_streak_days')
    search_fields = ('user__username', 'user__email')
    list_filter = ('tier', 'level', 'created_at')
    readonly_fields = ('created_at', 'updated_at', 'lifetime_points')


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'points_reward', 'condition_value', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('category', 'is_active', 'created_at')


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ('user', 'achievement', 'earned_at', 'notified')
    search_fields = ('user__username', 'achievement__name')
    list_filter = ('achievement__category', 'earned_at', 'notified')
    readonly_fields = ('earned_at',)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'points_earned', 'created_at')
    search_fields = ('user__username', 'description')
    list_filter = ('activity_type', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(UserStreak)
class UserStreakAdmin(admin.ModelAdmin):
    list_display = ('user', 'streak_count', 'best_streak_count', 'total_active_days')
    search_fields = ('user__username',)
    readonly_fields = ('current_streak_date',)


@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'period', 'rank', 'points', 'updated_at')
    search_fields = ('user__username',)
    list_filter = ('period', 'period_start')
    readonly_fields = ('updated_at',)
