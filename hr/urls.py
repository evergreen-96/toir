from django.urls import path
from .views import (
    HRListView,
    HRDetailView,
    HRCreateView,
    HRUpdateView,
    HumanResourceDeleteView,
    hr_manager_autocomplete,
    hr_job_title_autocomplete,
    export_hr_csv,
)

app_name = "hr"

urlpatterns = [
    # Основные CRUD URL
    path("", HRListView.as_view(), name="hr_list"),
    path("<int:pk>/", HRDetailView.as_view(), name="hr_detail"),
    path("new/", HRCreateView.as_view(), name="hr_new"),
    path("<int:pk>/edit/", HRUpdateView.as_view(), name="hr_edit"),
    path("<int:pk>/delete/", HumanResourceDeleteView.as_view(), name="hr_delete"),

    # AJAX endpoints
    path("ajax/managers/", hr_manager_autocomplete, name="hr_manager_autocomplete"),
    path("ajax/job-titles/", hr_job_title_autocomplete, name="hr_job_title_autocomplete"),
    # path("ajax/org-chart/", ajax_get_org_chart, name="ajax_get_org_chart"),

    # Экспорт
    path("export/csv/", export_hr_csv, name="export_csv"),

    # Дополнительные страницы (можно добавить позже)
    # path("org-chart/", OrgChartView.as_view(), name="org_chart"),
    # path("reports/", HRReportView.as_view(), name="reports"),
]