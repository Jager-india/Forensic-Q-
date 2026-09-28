from django.urls import path

from . import views

app_name = "q_chat"

urlpatterns = [
    path("", views.chat_dashboard_view, name="dashboard"),
    path("upload/", views.upload_chat_view, name="upload"),
    path("channel/<uuid:channel_id>/", views.channel_detail_view, name="channel_detail"),
    path("channel/<uuid:channel_id>/delete/", views.delete_channel_view, name="delete_channel"),
    path("channel/<uuid:channel_id>/api/messages/", views.messages_api_view, name="messages_api"),
]
