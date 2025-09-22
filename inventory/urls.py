from django.urls import path
from .views import (
    WarehouseListView, WarehouseDetailView, warehouse_create, warehouse_update, WarehouseDeleteView,
    MaterialListView, MaterialDetailView, material_create, material_update, MaterialDeleteView,
)

app_name = "inventory"

urlpatterns = [
    path("warehouses/", WarehouseListView.as_view(), name="warehouse_list"),
    path("warehouses/new/", warehouse_create, name="warehouse_new"),
    path("warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse_detail"),
    path("warehouses/<int:pk>/edit/", warehouse_update, name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", WarehouseDeleteView.as_view(), name="warehouse_delete"),

    path("materials/", MaterialListView.as_view(), name="material_list"),
    path("materials/new/", material_create, name="material_new"),
    path("materials/<int:pk>/", MaterialDetailView.as_view(), name="material_detail"),
    path("materials/<int:pk>/edit/", material_update, name="material_edit"),
    path("materials/<int:pk>/delete/", MaterialDeleteView.as_view(), name="material_delete"),
]
