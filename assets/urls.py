from django.urls import path
from .views import WorkstationListView, WorkstationDetailView, ws_create, ws_update, WorkstationDeleteView

app_name = "assets"

urlpatterns = [
    path("", WorkstationListView.as_view(), name="asset_list"),
    path("<int:pk>/", WorkstationDetailView.as_view(), name="asset_detail"),
    path("new/", ws_create, name="asset_new"),
    path("<int:pk>/edit/", ws_update, name="asset_edit"),
    path("<int:pk>/delete/", WorkstationDeleteView.as_view(), name="asset_delete"),
]