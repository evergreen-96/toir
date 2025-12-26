from django.urls import path
from .views import (
    WarehouseListView, WarehouseDetailView, WarehouseCreateView,
    WarehouseUpdateView, WarehouseDeleteView,
    MaterialListView, MaterialDetailView, MaterialCreateView,
    MaterialUpdateView, MaterialDeleteView,
)

app_name = "inventory"

urlpatterns = [
    # Warehouse URLs
    path("warehouses/", WarehouseListView.as_view(), name="warehouse_list"),
    path("warehouses/new/", WarehouseCreateView.as_view(), name="warehouse_new"),
    path("warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse_detail"),
    path("warehouses/<int:pk>/edit/", WarehouseUpdateView.as_view(), name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", WarehouseDeleteView.as_view(), name="warehouse_delete"),

    # Material URLs
    path("materials/", MaterialListView.as_view(), name="material_list"),
    path("materials/new/", MaterialCreateView.as_view(), name="material_new"),
    path("materials/<int:pk>/", MaterialDetailView.as_view(), name="material_detail"),
    path("materials/<int:pk>/edit/", MaterialUpdateView.as_view(), name="material_edit"),
    path("materials/<int:pk>/delete/", MaterialDeleteView.as_view(), name="material_delete"),
]