from django.conf import settings
from django.db import models


class Route(models.Model):
    STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    route_name = models.CharField(max_length=100)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNED')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_routes'
    )

    assigned_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_routes'
    )

    total_bins = models.PositiveIntegerField(default=0)
    total_distance_km = models.FloatField(default=0.0)

    collected_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    pending_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    optimizer_result = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.route_name


class RouteStop(models.Model):
    STOP_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COLLECTED', 'Collected'),
        ('SKIPPED', 'Skipped'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    bin = models.ForeignKey('bins.Bin', on_delete=models.CASCADE, related_name='route_stops')

    stop_order = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STOP_STATUS_CHOICES, default='PENDING')

    estimated_arrival = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['stop_order']
        unique_together = ('route', 'bin', 'stop_order')

    def __str__(self):
        return f"{self.route.route_name} - Stop {self.stop_order} - {self.bin.bin_id}"


class RouteActivity(models.Model):
    ACTION_CHOICES = [
        ('ROUTE_CREATED', 'Route Created'),
        ('ROUTE_ASSIGNED', 'Route Assigned'),
        ('STOP_COLLECTED', 'Stop Collected'),
        ('STOP_SKIPPED', 'Stop Skipped'),
        ('ROUTE_COMPLETED', 'Route Completed'),
        ('BIN_RESET', 'Bin Reset'),
    ]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='activities')
    stop = models.ForeignKey(RouteStop, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.route.route_name} - {self.action}"

class DriverLocation(models.Model):
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='locations'
    )

    latitude = models.FloatField()
    longitude = models.FloatField()

    speed = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.driver} @ {self.latitude},{self.longitude}"