from django.urls import path

from .views import LocationListView, LocationDetailView, location_create, location_update, LocationDeleteView

app_name = "locations"

urlpatterns = [
    path("", LocationListView.as_view(), name="location_list"),
    path("new/", location_create, name="location_new"),
    path("<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("<int:pk>/edit/", location_update, name="location_edit"),
    path("<int:pk>/delete/", LocationDeleteView.as_view(), name="location_delete"),
]
