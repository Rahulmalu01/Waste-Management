from django.contrib import admin
from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        'bin',
        'alert_type',
        'status',
        'created_at',
        'resolved_at',
        'created_by_system',
    )
    list_filter = ('alert_type', 'status', 'created_at')
    search_fields = ('bin__bin_id', 'bin__name', 'message')