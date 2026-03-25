from django.contrib import admin
from .models import Route, RouteStop, RouteActivity


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        'route_name',
        'date',
        'status',
        'assigned_driver',
        'total_bins',
        'total_distance_km',
        'created_at',
    )
    list_filter = ('status', 'date')
    search_fields = ('route_name',)
    inlines = [RouteStopInline]


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ('route', 'bin', 'stop_order', 'status')
    list_filter = ('status',)
    search_fields = ('route__route_name', 'bin__bin_id', 'bin__name')


@admin.register(RouteActivity)
class RouteActivityAdmin(admin.ModelAdmin):
    list_display = ('route', 'action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('route__route_name', 'message')