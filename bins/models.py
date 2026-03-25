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