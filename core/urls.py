from django.urls import path

from . import views

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("login/", views.portal_login_view, name="portal_login"),
    path("logout/", views.portal_logout_view, name="portal_logout"),
    path("profiles/create/", views.create_profile_view, name="create_profile"),
    path("profiles/active/", views.set_active_profile_view, name="set_active_profile"),
    path("api/profiles/", views.profile_list_api_view, name="api_profiles"),
]
