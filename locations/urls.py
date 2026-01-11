"""
Locations URLs
==============
"""

from django.urls import path

from .views import (
    LocationListView,
    LocationTreeJsonView,
    LocationDetailView,
    location_create,
    location_update,
    LocationDeleteView,
)

app_name = "locations"

urlpatterns = [
    # Список (с деревом jsTree)
    path("", LocationListView.as_view(), name="location_list"),

    # AJAX: JSON для jsTree
    path("tree/json/", LocationTreeJsonView.as_view(), name="location_tree_json"),

    # CRUD
    path("new/", location_create, name="location_new"),
    path("<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("<int:pk>/edit/", location_update, name="location_edit"),
    path("<int:pk>/delete/", LocationDeleteView.as_view(), name="location_delete"),
]