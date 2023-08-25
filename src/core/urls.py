from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from django.contrib import admin

from wallet.api import api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("faucet.urls")),
    path('wallet/', api.urls)
    ] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
