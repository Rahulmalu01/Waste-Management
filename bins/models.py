import secrets
from django.db import models

class Bin(models.Model):
    STATUS_CHOICES = [
        ('EMPTY', 'Empty'),
        ('PARTIAL', 'Partial'),
        ('FULL', 'Full'),
        ('OFFLINE', 'Offline'),
    ]
    bin_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    location_name = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    bin_height_cm = models.FloatField(default=100.0)
    current_distance_cm = models.FloatField(default=0.0)
    fill_percentage = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='EMPTY')
    threshold_percentage = models.FloatField(default=80.0)
    device_key = models.CharField(max_length=128, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def calculate_fill_percentage(self, distance_cm):
        if self.bin_height_cm <= 0:
            return 0.0
        fill = ((self.bin_height_cm - distance_cm) / self.bin_height_cm) * 100
        return max(0.0, min(100.0, round(fill, 2)))
    def update_status(self):
        if self.fill_percentage >= self.threshold_percentage:
            self.status = 'FULL'
        elif self.fill_percentage > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'EMPTY'
    def save(self, *args, **kwargs):
        if not self.device_key:
            self.device_key = secrets.token_hex(32)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.bin_id} - {self.name}"

class BinReading(models.Model):
    bin = models.ForeignKey(Bin, on_delete=models.CASCADE, related_name='readings')
    distance_cm = models.FloatField()
    fill_percentage = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    raw_payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.bin.bin_id} - {self.fill_percentage}% at {self.created_at}"

class DeviceAuthLog(models.Model):
    bin_id_attempted = models.CharField(max_length=50, blank=True, null=True)
    provided_device_key = models.CharField(max_length=128, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    status = models.CharField(max_length=50)
    raw_payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.bin_id_attempted or 'UNKNOWN'} - {self.status}"

# ============================================
# INCENTIVE SYSTEM MODELS
# ============================================

class UserPoints(models.Model):
    """Track user points and rewards"""
    user = models.OneToOneField('account.CustomUser', on_delete=models.CASCADE, related_name='points_profile')
    total_points = models.IntegerField(default=0)
    lifetime_points = models.IntegerField(default=0)  # Total earned all time
    current_streak_days = models.IntegerField(default=0)
    best_streak_days = models.IntegerField(default=0)
    last_activity_date = models.DateField(blank=True, null=True)
    level = models.IntegerField(default=1)  # 1-10 levels based on points
    tier = models.CharField(
        max_length=20, 
        choices=[
            ('BRONZE', 'Bronze'),
            ('SILVER', 'Silver'),
            ('GOLD', 'Gold'),
            ('PLATINUM', 'Platinum'),
        ],
        default='BRONZE'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def update_tier(self):
        """Update tier based on total points"""
        if self.total_points >= 5000:
            self.tier = 'PLATINUM'
        elif self.total_points >= 2000:
            self.tier = 'GOLD'
        elif self.total_points >= 800:
            self.tier = 'SILVER'
        else:
            self.tier = 'BRONZE'
    
    def update_level(self):
        """Update level based on total points"""
        self.level = min(10, max(1, self.total_points // 500 + 1))
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} points ({self.tier})"


class Achievement(models.Model):
    """Define available achievements"""
    CATEGORY_CHOICES = [
        ('REPORTING', 'Reporting'),
        ('CONSISTENCY', 'Consistency'),
        ('COMMUNITY', 'Community'),
        ('EXPLORATION', 'Exploration'),
        ('MILESTONE', 'Milestone'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    icon = models.CharField(max_length=50, default='badge')  # Bootstrap icon class
    color = models.CharField(max_length=20, default='primary')  # Bootstrap color
    points_reward = models.IntegerField(default=10)
    requirement = models.CharField(max_length=255)  # Description of requirement
    condition_value = models.IntegerField(default=1)  # Threshold to achieve
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    class Meta:
        ordering = ['category', 'name']


class UserAchievement(models.Model):
    """Track achievements earned by users"""
    user = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='achievements_earned')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"


class ActivityLog(models.Model):
    """Log user activities that earn points"""
    ACTIVITY_TYPES = [
        ('BIN_REPORT', 'Bin Report'),
        ('BIN_CLEARED', 'Bin Cleared'),
        ('DAILY_VISIT', 'Daily Visit'),
        ('ZONE_VISIT', 'Zone Visit'),
        ('FEEDBACK', 'Feedback'),
        ('COMMUNITY_ACTION', 'Community Action'),
        ('CONSISTENCY_BONUS', 'Consistency Bonus'),
    ]
    
    user = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    points_earned = models.IntegerField(default=0)
    description = models.CharField(max_length=255, blank=True)
    related_bin = models.ForeignKey(Bin, on_delete=models.SET_NULL, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)  # Store additional data
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} (+{self.points_earned})"
    
    class Meta:
        ordering = ['-created_at']


class UserStreak(models.Model):
    """Track user consistency streaks"""
    user = models.OneToOneField('account.CustomUser', on_delete=models.CASCADE, related_name='streak_info')
    current_streak_date = models.DateField(auto_now=True)
    streak_count = models.IntegerField(default=0)
    best_streak_count = models.IntegerField(default=0)
    last_broken_date = models.DateField(blank=True, null=True)
    total_active_days = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.streak_count} day streak"


class Leaderboard(models.Model):
    """Leaderboard rankings"""
    PERIOD_CHOICES = [
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('ALLTIME', 'All Time'),
    ]
    
    user = models.ForeignKey('account.CustomUser', on_delete=models.CASCADE, related_name='leaderboard_entries')
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    rank = models.IntegerField()
    points = models.IntegerField()
    activities_count = models.IntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'period', 'period_start']
        ordering = ['period', 'rank']
    
    def __str__(self):
        return f"{self.period} - {self.user.username} (Rank #{self.rank})"
