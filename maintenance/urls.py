from django.urls import path
from .views import (
    # Work Orders
    WorkOrderListView, WorkOrderDetailView, workorder_create, workorder_update, WorkOrderDeleteView,
    # Planned Orders
    PlannedOrderListView, planned_order_create, planned_order_update, planned_order_run_now, PlannedOrderDeleteView,
)

app_name = "maintenance"

urlpatterns = [
    # Рабочие задачи
    path("workorders/", WorkOrderListView.as_view(), name="wo_list"),
    path("workorders/new/", workorder_create, name="wo_new"),
    path("workorders/<int:pk>/", WorkOrderDetailView.as_view(), name="wo_detail"),
    path("workorders/<int:pk>/edit/", workorder_update, name="wo_edit"),
    path("workorders/<int:pk>/delete/", WorkOrderDeleteView.as_view(), name="wo_delete"),

    # Плановые обслуживания
    path("plans/", PlannedOrderListView.as_view(), name="plan_list"),
    path("plans/new/", planned_order_create, name="plan_new"),
    path("plans/<int:pk>/edit/", planned_order_update, name="plan_edit"),
    path("plans/<int:pk>/delete/", PlannedOrderDeleteView.as_view(), name="plan_delete"),
    path("plans/<int:pk>/run-now/", planned_order_run_now, name="plan_run_now"),
]
