# toir_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from maintenance.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),

    # namespaces
    path("", include(("maintenance.urls", "maintenance"), namespace="maintenance")),
    path("assets/", include(("assets.urls", "assets"), namespace="assets")),
    path("inventory/", include(("inventory.urls", "inventory"), namespace="inventory")),
    path("locations/", include(("locations.urls", "locations"), namespace="locations")),
    path("hr/", include(("hr.urls", "hr"), namespace="hr")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
