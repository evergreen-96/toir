from django.urls import path
from .views import HRListView, HRDetailView, hr_create, hr_update, HumanResourceDeleteView

app_name = "hr"

urlpatterns = [
    path("", HRListView.as_view(), name="hr_list"),
    path("new/", hr_create, name="hr_new"),
    path("<int:pk>/", HRDetailView.as_view(), name="hr_detail"),
    path("<int:pk>/edit/", hr_update, name="hr_edit"),
    path("<int:pk>/delete/", HumanResourceDeleteView.as_view(), name="hr_delete"),
]
