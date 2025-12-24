from django.urls import path
from django.views.generic import DetailView

from .models import PlannedOrder
from .views import (
    # Work Orders
    WorkOrderListView, WorkOrderDetailView, workorder_create, workorder_update, WorkOrderDeleteView,
    # Planned Orders
    PlannedOrderListView, planned_order_create, planned_order_update, planned_order_run_now, PlannedOrderDeleteView,
    planned_order_preview,  # ✅ добавили
    wo_set_status, get_workstations_by_location, PlannedOrderDetailView,
)

app_name = "maintenance"

urlpatterns = [
    # Рабочие задачи
    path("workorders/", WorkOrderListView.as_view(), name="wo_list"),
    path("workorders/new/", workorder_create, name="wo_new"),
    path("workorders/<int:pk>/", WorkOrderDetailView.as_view(), name="wo_detail"),
    path("workorders/<int:pk>/edit/", workorder_update, name="wo_edit"),
    path("workorders/<int:pk>/delete/", WorkOrderDeleteView.as_view(), name="wo_delete"),
    path("workorders/<int:pk>/set-status/<str:status>/", wo_set_status, name="wo_set_status"),
    path("ajax/workstations-by-location/", get_workstations_by_location, name="ajax_workstations_by_location"),
    # path(
    #     "workorders/files/<int:pk>/delete/",
    #     workorder_attachment_delete,
    #     name="wo_file_delete"
    # ),

    # Плановые обслуживания
    path("plans/", PlannedOrderListView.as_view(), name="plan_list"),
    path("plans/<int:pk>/", PlannedOrderDetailView.as_view(), name="plan_detail"),
    path("plans/new/", planned_order_create, name="plan_new"),
    path("plans/<int:pk>/edit/", planned_order_update, name="plan_edit"),
    path("plans/<int:pk>/delete/", PlannedOrderDeleteView.as_view(), name="plan_delete"),
    path("plans/<int:pk>/run-now/", planned_order_run_now, name="plan_run_now"),

    # ✅ Превью календаря/дат на 2 месяца (AJAX)
    path("plans/preview/", planned_order_preview, name="plan_preview"),
]
