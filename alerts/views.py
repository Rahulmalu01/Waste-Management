from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Alert

@login_required
def alert_list_view(request):
    alert_list = Alert.objects.select_related('bin', 'resolved_by').order_by('-created_at')
    paginator = Paginator(alert_list, 10)  # 🔥 10 alerts per page
    page_number = request.GET.get('page')
    alerts = paginator.get_page(page_number)
    return render(request, 'alert_list.html', {'alerts': alerts})
