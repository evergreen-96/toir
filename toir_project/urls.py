"""
URL configuration for toir_project project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from maintenance.views import home

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Home dashboard
    path('', home, name='home'),

    # App URLs with namespaces
    path('maintenance/', include(('maintenance.urls', 'maintenance'), namespace='maintenance')),
    path('assets/', include(('assets.urls', 'assets'), namespace='assets')),
    path('inventory/', include(('inventory.urls', 'inventory'), namespace='inventory')),
    path('locations/', include(('locations.urls', 'locations'), namespace='locations')),
    path('hr/', include(('hr.urls', 'hr'), namespace='hr')),

    # Third party
    path('select2/', include('django_select2.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


