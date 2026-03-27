from django.urls import path
from .views import (
    ingest_bin_data, bin_list_view, bin_dashboard_view, bin_map_view, 
    ingest_sensor_data, user_points_view, leaderboard_view, 
    achievements_view, activity_log_view
)

urlpatterns = [
    path('api/ingest-bin-data/', ingest_bin_data, name='ingest_bin_data'),
    path('', bin_list_view, name='bin_list'),
    path('dashboard/', bin_dashboard_view, name='bin_dashboard'),
    path('map/', bin_map_view, name='bin_map'),
    path('ingest/', ingest_sensor_data, name='ingest_sensor_data'),
    
    # Incentive System URLs
    path('incentives/points/', user_points_view, name='user_points'),
    path('incentives/leaderboard/', leaderboard_view, name='leaderboard'),
    path('incentives/achievements/', achievements_view, name='achievements'),
    path('incentives/activity-log/', activity_log_view, name='activity_log'),
]
