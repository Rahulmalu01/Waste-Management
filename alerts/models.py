from django.conf import settings
from django.db import models


class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('BIN_FULL', 'Bin Full'),
        ('BIN_OFFLINE', 'Bin Offline'),
        ('DEVICE_ERROR', 'Device Error'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('RESOLVED', 'Resolved'),
    ]

    bin = models.ForeignKey('bins.Bin', on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, default='BIN_FULL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')

    message = models.TextField(blank=True, null=True)

    telegram_sent = models.BooleanField(default=False)
    telegram_sent_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    created_by_system = models.BooleanField(default=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='resolved_alerts'
    )

    def __str__(self):
        return f"{self.bin.bin_id} - {self.alert_type} - {self.status}"