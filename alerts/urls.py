from django.urls import path
from .views import alert_list_view

urlpatterns = [
    path('', alert_list_view, name='alert_list'),
]