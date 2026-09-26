from django.urls import path

from . import views

app_name = "q_scan"

urlpatterns = [
    path("", views.scan_dashboard_view, name="dashboard"),
    path("upload/", views.upload_scan_csv_view, name="upload_csv"),
    path("devices/<uuid:device_id>/", views.device_detail_view, name="device_detail"),
    path("devices/<uuid:device_id>/delete/", views.delete_device_view, name="delete_device"),
    path("hits/<uuid:hit_id>/review/", views.review_hit_api_view, name="review_hit_api"),
    path("export/csv/", views.export_hits_csv_view, name="export_csv"),
    path("download/<str:filename>/", views.download_tool_file_view, name="download_tool"),
]
