from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import HumanResource


@admin.register(HumanResource)
class HumanResourceAdmin(SimpleHistoryAdmin):
    list_display = ("name", "job_title", "manager")
    search_fields = ("name", "job_title")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            db_field.name == "manager"
            and request.resolver_match
            and request.resolver_match.kwargs.get("object_id")
        ):
            # исключаем самого себя из выбора начальника
            obj_id = request.resolver_match.kwargs["object_id"]
            kwargs["queryset"] = HumanResource.objects.exclude(pk=obj_id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение сотрудника"
        else:
            obj._change_reason = "admin: создание сотрудника"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
