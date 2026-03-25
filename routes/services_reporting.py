from datetime import timedelta
from django.db.models import Count, Avg, Q
from django.utils import timezone

from bins.models import Bin, BinReading
from alerts.models import Alert
from account.models import CustomUser
from .models import Route, RouteStop


def get_report_range(report_type='daily'):
    today = timezone.now()
    if report_type == 'weekly':
        start = today - timedelta(days=7)
    else:
        start = today - timedelta(days=1)
    return start, today


def get_report_summary(report_type='daily'):
    start, end = get_report_range(report_type)

    routes = Route.objects.filter(created_at__range=(start, end))
    stops = RouteStop.objects.filter(route__created_at__range=(start, end))
    readings = BinReading.objects.filter(created_at__range=(start, end))
    alerts = Alert.objects.filter(created_at__range=(start, end))

    summary = {
        'report_type': report_type.title(),
        'start': start,
        'end': end,
        'total_routes': routes.count(),
        'completed_routes': routes.filter(status='COMPLETED').count(),
        'in_progress_routes': routes.filter(status='IN_PROGRESS').count(),
        'assigned_routes': routes.filter(status='ASSIGNED').count(),
        'cancelled_routes': routes.filter(status='CANCELLED').count(),
        'total_collections': stops.filter(status='COLLECTED').count(),
        'skipped_stops': stops.filter(status='SKIPPED').count(),
        'pending_stops': stops.filter(status='PENDING').count(),
        'average_fill_level': round(readings.aggregate(avg_fill=Avg('fill_percentage'))['avg_fill'] or 0, 2),
        'full_alerts': alerts.filter(alert_type='BIN_FULL').count(),
        'offline_alerts': alerts.filter(alert_type='BIN_OFFLINE').count(),
        'active_alerts': alerts.filter(status='ACTIVE').count(),
    }

    problematic_bins = Bin.objects.annotate(
        skipped_count=Count('route_stops', filter=Q(route_stops__status='SKIPPED')),
        alert_count=Count('alerts')
    ).order_by('-skipped_count', '-alert_count')[:5]

    driver_summary = CustomUser.objects.filter(role='DRIVER').annotate(
        assigned_routes_count=Count(
            'assigned_routes',
            filter=Q(assigned_routes__created_at__range=(start, end)),
            distinct=True
        ),
        completed_routes_count=Count(
            'assigned_routes',
            filter=Q(
                assigned_routes__status='COMPLETED',
                assigned_routes__created_at__range=(start, end)
            ),
            distinct=True
        ),
        collected_stops_count=Count(
            'assigned_routes__stops',
            filter=Q(
                assigned_routes__stops__status='COLLECTED',
                assigned_routes__created_at__range=(start, end)
            )
        ),
        skipped_stops_count=Count(
            'assigned_routes__stops',
            filter=Q(
                assigned_routes__stops__status='SKIPPED',
                assigned_routes__created_at__range=(start, end)
            )
        ),
    )

    return {
        'summary': summary,
        'problematic_bins': problematic_bins,
        'driver_summary': driver_summary,
    }


def build_summary_text(report_data):
    summary = report_data['summary']
    problematic_bins = report_data['problematic_bins']
    driver_summary = report_data['driver_summary']

    lines = [
        f"{summary['report_type']} Waste Management Report",
        f"Period: {summary['start'].strftime('%Y-%m-%d %H:%M')} to {summary['end'].strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Total Routes: {summary['total_routes']}",
        f"Completed Routes: {summary['completed_routes']}",
        f"In Progress Routes: {summary['in_progress_routes']}",
        f"Assigned Routes: {summary['assigned_routes']}",
        f"Cancelled Routes: {summary['cancelled_routes']}",
        f"Total Collections: {summary['total_collections']}",
        f"Skipped Stops: {summary['skipped_stops']}",
        f"Pending Stops: {summary['pending_stops']}",
        f"Average Fill Level: {summary['average_fill_level']}%",
        f"Full Alerts: {summary['full_alerts']}",
        f"Offline Alerts: {summary['offline_alerts']}",
        f"Active Alerts: {summary['active_alerts']}",
        "",
        "Top Problematic Bins:",
    ]

    for bin_obj in problematic_bins:
        lines.append(
            f"- {bin_obj.bin_id} | {bin_obj.name} | Skipped: {getattr(bin_obj, 'skipped_count', 0)} | Alerts: {getattr(bin_obj, 'alert_count', 0)}"
        )

    lines.append("")
    lines.append("Driver Summary:")

    for driver in driver_summary:
        lines.append(
            f"- {driver.username}: Assigned={driver.assigned_routes_count}, Completed={driver.completed_routes_count}, Collected={driver.collected_stops_count}, Skipped={driver.skipped_stops_count}"
        )

    return "\n".join(lines)