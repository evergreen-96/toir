from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html
from django.db.models import Count

from .models import HumanResource


@admin.register(HumanResource)
class HumanResourceAdmin(SimpleHistoryAdmin):
    # =========================
    # LIST
    # =========================
    list_display = (
        "name",
        "job_title",
        "manager",
        "subordinates_count",
        "last_change",
    )

    search_fields = (
        "name",
        "job_title",
    )

    list_select_related = (
        "manager",
    )

    ordering = ("name",)

    # =========================
    # DETAIL
    # =========================
    readonly_fields = ()

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name",
                "job_title",
                "manager",
            )
        }),
    )

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "job_title",
        "manager",
    )

    history_list_filter = (
        "job_title",
    )

    # =========================
    # QUERYSET OPTIMIZATION
    # =========================
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _sub_cnt=Count("subordinates")
        )

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description="Подчинённые")
    def subordinates_count(self, obj):
        return obj._sub_cnt or "—"

    @admin.display(description="Последнее изменение")
    def last_change(self, obj):
        h = obj.history.first()
        if not h:
            return "—"
        return format_html(
            "{}<br><small>{}</small>",
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            h.history_user or "system",
        )

    # =========================
    # FORM LOGIC
    # =========================
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if (
            db_field.name == "manager"
            and request.resolver_match
            and request.resolver_match.kwargs.get("object_id")
        ):
            obj_id = request.resolver_match.kwargs["object_id"]
            kwargs["queryset"] = HumanResource.objects.exclude(pk=obj_id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # =========================
    # SAVE
    # =========================
    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение сотрудника"
        else:
            obj._change_reason = "admin: создание сотрудника"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
