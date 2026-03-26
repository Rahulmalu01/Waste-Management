from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def index(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

@login_required
def nearby_bins(request):
    return render(request, 'nearby_bins.html')

@login_required
def report_issue(request):
    return render(request, 'report_issue.html')

@login_required
def my_reports(request):
    user_reports=[]
    return render(request, 'my_reports.html', {'reports': user_reports})
