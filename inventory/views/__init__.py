from .warehouse import (
    WarehouseListView,
    WarehouseDetailView,
    WarehouseCreateView,
    WarehouseUpdateView,
    WarehouseDeleteView,
)

from .material import (
    MaterialListView,
    MaterialDetailView,
    MaterialCreateView,
    MaterialUpdateView,
    MaterialDeleteView,
)

__all__ = [
    # Warehouse views
    'WarehouseListView',
    'WarehouseDetailView',
    'WarehouseCreateView',
    'WarehouseUpdateView',
    'WarehouseDeleteView',

    # Material views
    'MaterialListView',
    'MaterialDetailView',
    'MaterialCreateView',
    'MaterialUpdateView',
    'MaterialDeleteView',
]