from django.utils import timezone
from .models import Alert
from .telegram_service import send_telegram_message


def format_bin_full_message(bin_obj):
    location_text = bin_obj.location_name if bin_obj.location_name else 'Unknown location'
    maps_link = f"https://www.google.com/maps?q={bin_obj.latitude},{bin_obj.longitude}"
    return (
        f"🚮 <b>Bin Full Alert</b>\n\n"
        f"<b>Bin ID:</b> {bin_obj.bin_id}\n"
        f"<b>Bin Name:</b> {bin_obj.name}\n"
        f"<b>Fill Level:</b> {bin_obj.fill_percentage}%\n"
        f"<b>Location:</b> {location_text}\n"
        f"<b>Coordinates:</b> {bin_obj.latitude}, {bin_obj.longitude}\n"
        f"<b>Map:</b> {maps_link}\n"
        f"<b>Status:</b> {bin_obj.status}"
    )

def format_bin_offline_message(bin_obj):
    location_text = bin_obj.location_name if bin_obj.location_name else 'Unknown location'
    maps_link = f"https://www.google.com/maps?q={bin_obj.latitude},{bin_obj.longitude}"
    return (
        f"⚠️ <b>Bin Offline Alert</b>\n\n"
        f"<b>Bin ID:</b> {bin_obj.bin_id}\n"
        f"<b>Bin Name:</b> {bin_obj.name}\n"
        f"<b>Location:</b> {location_text}\n"
        f"<b>Coordinates:</b> {bin_obj.latitude}, {bin_obj.longitude}\n"
        f"<b>Last Seen:</b> {bin_obj.last_seen}\n"
        f"<b>Map:</b> {maps_link}\n"
        f"<b>Status:</b> OFFLINE"
    )

def create_alert_if_not_exists(bin_obj, alert_type, message):
    existing_active_alert = Alert.objects.filter(
        bin=bin_obj,
        alert_type=alert_type,
        status='ACTIVE'
    ).first()
    if existing_active_alert:
        return existing_active_alert, False
    alert = Alert.objects.create(
        bin=bin_obj,
        alert_type=alert_type,
        status='ACTIVE',
        message=message,
        created_by_system=True,
    )
    return alert, True

def create_bin_full_alert(bin_obj):
    message = (
        f"Bin {bin_obj.bin_id} is full. "
        f"Fill level: {bin_obj.fill_percentage}%. "
        f"Location: {bin_obj.location_name or 'Unknown'}"
    )
    alert, created = create_alert_if_not_exists(bin_obj, 'BIN_FULL', message)
    if created:
        telegram_message = format_bin_full_message(bin_obj)
        telegram_result = send_telegram_message(telegram_message)
        if telegram_result.get('success'):
            alert.telegram_sent = True
            alert.telegram_sent_at = timezone.now()
            alert.save()
    return alert, created

def create_bin_offline_alert(bin_obj):
    message = (
        f"Bin {bin_obj.bin_id} is offline. "
        f"Last seen: {bin_obj.last_seen}. "
        f"Location: {bin_obj.location_name or 'Unknown'}"
    )
    alert, created = create_alert_if_not_exists(bin_obj, 'BIN_OFFLINE', message)
    if created:
        telegram_message = format_bin_offline_message(bin_obj)
        telegram_result = send_telegram_message(telegram_message)
        if telegram_result.get('success'):
            alert.telegram_sent = True
            alert.telegram_sent_at = timezone.now()
            alert.save()
    return alert, created

def resolve_alerts_by_type(bin_obj, alert_type, resolved_by=None):
    active_alerts = Alert.objects.filter(
        bin=bin_obj,
        alert_type=alert_type,
        status='ACTIVE'
    )
    resolved_count = 0
    for alert in active_alerts:
        alert.status = 'RESOLVED'
        alert.resolved_at = timezone.now()
        alert.resolved_by = resolved_by
        alert.save()
        resolved_count += 1
    return resolved_count

def resolve_bin_full_alert(bin_obj, resolved_by=None):
    return resolve_alerts_by_type(bin_obj, 'BIN_FULL', resolved_by=resolved_by)

def resolve_bin_offline_alert(bin_obj, resolved_by=None):
    return resolve_alerts_by_type(bin_obj, 'BIN_OFFLINE', resolved_by=resolved_by)