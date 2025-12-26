from django.contrib import admin
from django.db import models
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
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
        "is_active_display",
        "last_change",
    )

    list_filter = (
        "is_active",
        "job_title",
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
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Основная информация"), {
            "fields": (
                "name",
                "job_title",
                "manager",
                "is_active",
            )
        }),
        (_("Системная информация"), {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "job_title",
        "manager",
        "is_active",
    )

    # =========================
    # QUERYSET OPTIMIZATION
    # =========================
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _sub_cnt=models.Count("subordinates")
        )

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description=_("Подчинённые"))
    def subordinates_count(self, obj):
        return obj._sub_cnt or "—"

    @admin.display(description=_("Активен"))
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">●</span> {}',
                _("Да")
            )
        return format_html(
            '<span style="color: red;">●</span> {}',
            _("Нет")
        )

    @admin.display(description=_("Последнее изменение"))
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