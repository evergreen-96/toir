# =============================================================================
# ЗАМЕНИТЬ ФАЙЛ assets/urls.py ПОЛНОСТЬЮ
# =============================================================================

from django.urls import path
from .views import (
    WorkstationListView,
    WorkstationDetailView,
    WorkstationCreateView,
    WorkstationUpdateView,
    WorkstationDeleteView,
    ajax_get_workstation_status,
    ajax_update_workstation_status,
    ajax_type_name_autocomplete,  # НОВЫЙ ИМПОРТ
    # ajax_get_workstation_info,
    export_workstations_csv,
)

app_name = "assets"

urlpatterns = [
    # Основные CRUD URL
    path("", WorkstationListView.as_view(), name="asset_list"),
    path("<int:pk>/", WorkstationDetailView.as_view(), name="asset_detail"),
    path("new/", WorkstationCreateView.as_view(), name="asset_new"),
    path("<int:pk>/edit/", WorkstationUpdateView.as_view(), name="asset_edit"),
    path("<int:pk>/delete/", WorkstationDeleteView.as_view(), name="asset_delete"),

    # AJAX endpoints
    path("ajax/status/get/", ajax_get_workstation_status, name="ajax_get_status"),
    path("ajax/status/update/", ajax_update_workstation_status, name="ajax_update_status"),
    path("ajax/type-name/autocomplete/", ajax_type_name_autocomplete, name="ajax_type_autocomplete"),  # НОВЫЙ URL
    # path("ajax/info/", ajax_get_workstation_info, name="ajax_get_info"),

    # Экспорт
    path("export/csv/", export_workstations_csv, name="export_csv"),
]