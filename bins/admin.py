from django.contrib import admin
from .models import Bin, BinReading, DeviceAuthLog


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