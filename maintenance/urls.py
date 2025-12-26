from django.urls import path

from assets.views import ajax_get_workstation_status, ajax_update_workstation_status
from . import views

app_name = "maintenance"

urlpatterns = [
    # ============================================
    # РАБОЧИЕ ЗАДАЧИ (WORK ORDERS)
    # ============================================

    # Список всех рабочих задач
    path("workorders/",
         views.WorkOrderListView.as_view(),
         name="wo_list"),

    # Создание новой задачи
    path("workorders/new/",
         views.workorder_create,
         name="wo_new"),

    # Детальная страница задачи
    path("workorders/<int:pk>/",
         views.WorkOrderDetailView.as_view(),
         name="wo_detail"),

    # Редактирование задачи
    path("workorders/<int:pk>/edit/",
         views.workorder_update,
         name="wo_edit"),

    # Удаление задачи (AJAX)
    path("workorders/<int:pk>/delete/",
         views.WorkOrderDeleteView.as_view(),
         name="wo_delete"),

    # Изменение статуса задачи
    path("workorders/<int:pk>/set-status/<str:status>/",
         views.wo_set_status,
         name="wo_set_status"),

    # ============================================
    # ПЛАНОВЫЕ РАБОТЫ (PLANNED ORDERS)
    # ============================================

    # Список всех плановых работ
    path("plans/",
         views.PlannedOrderListView.as_view(),
         name="plan_list"),

    # Детальная страница плана
    path("plans/<int:pk>/",
         views.PlannedOrderDetailView.as_view(),
         name="plan_detail"),

    # Создание нового плана
    path("plans/new/",
         views.planned_order_create,
         name="plan_new"),

    # Редактирование плана
    path("plans/<int:pk>/edit/",
         views.planned_order_update,
         name="plan_edit"),

    # Удаление плана (AJAX)
    path("plans/<int:pk>/delete/",
         views.PlannedOrderDeleteView.as_view(),
         name="plan_delete"),

    # Ручной запуск плана (создание задачи)
    path("plans/<int:pk>/run-now/",
         views.planned_order_run_now,
         name="plan_run_now"),

    # ============================================
    # AJAX И ВСПОМОГАТЕЛЬНЫЕ ЭНДПОИНТЫ
    # ============================================

    # Получение оборудования по выбранной локации (AJAX)
    path("ajax/workstations-by-location/",
         views.get_workstations_by_location,
         name="ajax_workstations_by_location"),

    # Поиск материалов (AJAX для Select2)
    path('ajax/material-search/',
         views.ajax_material_search,
         name='ajax_material_search'),

    # Превью дат запуска плана (AJAX)
    path("plans/preview/",
         views.planned_order_preview,
         name="plan_preview"),

    # ============================================
    # ИНТЕГРАЦИЯ С МОДУЛЕМ ОБОРУДОВАНИЯ (ASSETS)
    # ============================================

    # Получение текущего статуса оборудования
    path("ajax/workstation-status/",
         ajax_get_workstation_status,
         name="ajax_workstation_status"),

    # Обновление статуса оборудования
    path("ajax/workstation-status/update/",
         ajax_update_workstation_status,
         name="ajax_workstation_status_update"),
]