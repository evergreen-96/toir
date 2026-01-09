"""
Inventory URLs - Склады и Материалы
===================================
"""

from django.urls import path

from .views import (
    # Warehouse
    WarehouseListView,
    WarehouseDetailView,
    warehouse_create,
    warehouse_update,
    WarehouseDeleteView,
    # Material
    MaterialListView,
    MaterialDetailView,
    material_create,
    material_update,
    MaterialDeleteView,
    # AJAX
    ajax_material_search,
    ajax_warehouse_search,
)

app_name = "inventory"

urlpatterns = [
    # ==========================================================================
    # WAREHOUSE
    # ==========================================================================
    path("warehouses/", WarehouseListView.as_view(), name="warehouse_list"),
    path("warehouses/new/", warehouse_create, name="warehouse_new"),
    path("warehouses/<int:pk>/", WarehouseDetailView.as_view(), name="warehouse_detail"),
    path("warehouses/<int:pk>/edit/", warehouse_update, name="warehouse_edit"),
    path("warehouses/<int:pk>/delete/", WarehouseDeleteView.as_view(), name="warehouse_delete"),
    
    # ==========================================================================
    # MATERIAL
    # ==========================================================================
    path("materials/", MaterialListView.as_view(), name="material_list"),
    path("materials/new/", material_create, name="material_new"),
    path("materials/<int:pk>/", MaterialDetailView.as_view(), name="material_detail"),
    path("materials/<int:pk>/edit/", material_update, name="material_edit"),
    path("materials/<int:pk>/delete/", MaterialDeleteView.as_view(), name="material_delete"),
    
    # ==========================================================================
    # AJAX ENDPOINTS
    # ==========================================================================
    path("api/materials/search/", ajax_material_search, name="ajax_material_search"),
    path("api/warehouses/search/", ajax_warehouse_search, name="ajax_warehouse_search"),
]
