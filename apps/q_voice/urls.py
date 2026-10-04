"""
Q-Voice URL Configuration
"""

from django.urls import path

from . import views

app_name = "q_voice"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path(
        "custodian/<str:custodian_name>/",
        views.custodian_detail_view,
        name="custodian_detail",
    ),
    path(
        "custodian/<str:custodian_name>/delete/",
        views.delete_custodian_view,
        name="delete_custodian",
    ),
    path(
        "recording/<uuid:recording_id>/",
        views.recording_detail_view,
        name="recording_detail",
    ),
    path(
        "recording/<uuid:recording_id>/delete/",
        views.delete_recording_view,
        name="delete_recording",
    ),
]
