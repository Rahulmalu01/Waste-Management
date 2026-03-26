from django.urls import path
from .views import (
    route_list_view,
    generate_route_view,
    assign_route_view,
    assigned_routes_view,
    route_detail_view,
    mark_stop_collected_view,
    mark_stop_skipped_view,
    analytics_dashboard_view,
    reports_home_view,
    export_reports_pdf_view,
    export_reports_excel_view,
    printable_reports_view,
    send_manual_report_view,
    update_driver_location,
    get_driver_location,
    live_map_view
)

urlpatterns = [
    path('', route_list_view, name='route_list'),
    path('generate/', generate_route_view, name='generate_route'),
    path('assign/<int:route_id>/', assign_route_view, name='assign_route'),
    path('my-routes/', assigned_routes_view, name='assigned_routes'),
    path('detail/<int:route_id>/', route_detail_view, name='route_detail'),
    path('stop/<int:stop_id>/collect/', mark_stop_collected_view, name='mark_stop_collected'),
    path('stop/<int:stop_id>/skip/', mark_stop_skipped_view, name='mark_stop_skipped'),
    path('analytics/', analytics_dashboard_view, name='analytics_dashboard'),

    path('reports/', reports_home_view, name='reports_home'),
    path('reports/pdf/', export_reports_pdf_view, name='export_reports_pdf'),
    path('reports/excel/', export_reports_excel_view, name='export_reports_excel'),
    path('reports/print/', printable_reports_view, name='printable_reports'),
    path('reports/send/<str:report_type>/', send_manual_report_view, name='send_manual_report'),

    path('driver/update-location/', update_driver_location, name='update_driver_location'),
    path('driver/location/<int:driver_id>/', get_driver_location, name='get_driver_location'),  
    path('live-map/<int:route_id>/', live_map_view, name='live_map'),  
]