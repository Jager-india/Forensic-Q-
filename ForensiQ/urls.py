from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("demo/", include("demo.urls")),
    path("mail/", include("q_mail.urls")),
    path("verify/", include("q_verify.urls")),
    path("scan/", include("q_scan.urls")),
    path("bank/", include("q_bank.urls")),
    path("chat/", include("q_chat.urls")),
    # path("voice/", include("q_voice.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
