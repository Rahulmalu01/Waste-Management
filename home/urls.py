from django.urls import path
from . import views

urlpatterns = [
    path('nearby-bins/', views.nearby_bins, name='nearby_bins'),
    path('report-issue/', views.report_issue, name='report_issue'),
    path('my-reports/', views.my_reports, name='my_reports'),

    path('', views.index, name='home'),
    path('about/', views.about, name='about'),
]
