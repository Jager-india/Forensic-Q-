"""
Q-Voice URL Configuration
"""

from django.urls import path

from . import views

app_name = "q_voice"

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
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
