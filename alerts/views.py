from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Alert


@login_required
def alert_list_view(request):
    alerts = Alert.objects.select_related('bin', 'resolved_by').order_by('-created_at')
    return render(request, 'alerts/alert_list.html', {'alerts': alerts})