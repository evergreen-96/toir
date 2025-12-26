from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.db.models import Count, Q
from django.utils import timezone

from simple_history.admin import SimpleHistoryAdmin

from .models import Workstation, WorkstationStatus, WorkstationGlobalState
from core.audit import build_change_reason


class StatusFilter(admin.SimpleListFilter):
    title = _("Статус оборудования")
    parameter_name = 'status_filter'

    def lookups(self, request, model_admin):
        return (
            ('under_warranty', _("На гарантии")),
            ('needs_attention', _("Требует внимания")),
            ('inactive', _("Неактивное")),
        )

    def queryset(self, request, queryset):
        if self.value() == 'under_warranty':
            return queryset.filter(
                warranty_until__gte=timezone.now().date(),
                status=WorkstationStatus.PROD
            )
        elif self.value() == 'needs_attention':
            return queryset.filter(
                Q(status=WorkstationStatus.PROBLEM) |
                Q(status=WorkstationStatus.MAINT)
            )
        elif self.value() == 'inactive':
            return queryset.filter(
                global_state=WorkstationGlobalState.ARCHIVED
            )
        return queryset


class LocationFilter(admin.RelatedFieldListFilter):
    def field_choices(self, field, request, model_admin):
        from locations.models import Location
        return [
            (location.id, f"{location.name} ({location.workstations.count()})")
            for location in Location.objects.annotate(
                workstation_count=Count('workstations')
            ).order_by('name')
        ]


@admin.register(Workstation)
class WorkstationAdmin(SimpleHistoryAdmin):
    # =========================
    # LIST VIEW
    # =========================
    list_display = (
        "photo_thumbnail",
        "name_with_link",
        "category_badge",
        "status_badge",
        "location_link",
        "responsible_link",
        "global_state_badge",
        "warranty_info",
        "last_change",
        "actions",
    )

    list_display_links = None

    list_filter = (
        StatusFilter,
        "global_state",
        "category",
        "status",
        ("location", LocationFilter),
    )

    search_fields = (
        "name",
        "serial_number",
        "inventory_number",
        "model",
        "manufacturer",
        "type_name",
        "location__name",
        "responsible__name",  # Используем name вместо user__username
    )

    list_select_related = (
        "location",
        "responsible",
    )

    list_per_page = 25

    ordering = ("name",)

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "photo_preview",
        "age_display",
        "warranty_status",
    )

    fieldsets = (
        (_("Основная информация"), {
            "fields": (
                "name",
                "category",
                "type_name",
                ("manufacturer", "model"),
                "photo",
                "photo_preview",
            ),
            "classes": ("collapse", "open"),
        }),
        (_("Состояние и статус"), {
            "fields": (
                ("global_state", "status"),
                ("location", "responsible"),
            )
        }),
        (_("Идентификация"), {
            "fields": (
                ("serial_number", "inventory_number"),
            )
        }),
        (_("Эксплуатация"), {
            "fields": (
                ("commissioning_date", "warranty_until"),
                "age_display",
                "warranty_status",
            )
        }),
        (_("Описание"), {
            "fields": ("description",)
        }),
        (_("Служебная информация"), {
            "fields": (
                ("created_at", "updated_at"),
                "created_by",
            ),
            "classes": ("collapse",),
        }),
    )

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "status",
        "location",
        "responsible",
        "global_state",
    )

    history_list_filter = (
        "status",
        "global_state",
    )

    # =========================
    # SAVE
    # =========================
    def save_model(self, request, obj, form, change):
        """
        Логируем изменения из admin
        """
        if not change:  # Создание нового
            obj.created_by = request.user

        obj._history_user = request.user
        obj._change_reason = build_change_reason(
            "admin: ручное изменение оборудования"
        )
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Обработка формсетов (если понадобятся)
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if hasattr(instance, '_history_user'):
                instance._history_user = request.user
                instance._change_reason = build_change_reason(
                    "admin: изменение через формсет"
                )
            instance.save()
        formset.save_m2m()

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description=_("Фото"))
    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                obj.photo.url
            )
        return "—"

    @admin.display(description=_("Оборудование"))
    def name_with_link(self, obj):
        url = reverse("admin:assets_workstation_change", args=[obj.pk])
        return format_html(
            '<a href="{}"><strong>{}</strong></a><br>'
            '<small class="text-muted">{}</small>',
            url, obj.name, obj.type_name
        )

    @admin.display(description=_("Категория"))
    def category_badge(self, obj):
        colors = {
            "main": "primary",
            "aux": "info",
            "meas": "success",
            "test": "warning",
            "other": "secondary",
        }
        color = colors.get(obj.category, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_category_display()
        )

    @admin.display(description=_("Статус"))
    def status_badge(self, obj):
        colors = {
            "prod": "success",
            "problem": "danger",
            "maint": "warning",
            "setup": "info",
            "reserved": "secondary",
            "decommissioned": "dark",
        }
        color = colors.get(obj.status, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description=_("Глобальное состояние"))
    def global_state_badge(self, obj):
        colors = {
            "active": "success",
            "arch": "secondary",
            "reserve": "info",
            "decommissioned": "dark",
        }
        color = colors.get(obj.global_state, "secondary")
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_global_state_display()
        )

    @admin.display(description=_("Локация"))
    def location_link(self, obj):
        if not obj.location:
            return "—"
        url = reverse("admin:locations_location_change", args=[obj.location.pk])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.location.name
        )

    @admin.display(description=_("Ответственный"))
    def responsible_link(self, obj):
        if not obj.responsible:
            return "—"
        url = reverse("admin:hr_humanresource_change", args=[obj.responsible.pk])
        name = str(obj.responsible)
        return format_html(
            '<a href="{}">{}</a>',
            url, name
        )

    @admin.display(description=_("Гарантия"))
    def warranty_info(self, obj):
        if not obj.warranty_until:
            return "—"

        today = timezone.now().date()
        if obj.warranty_until >= today:
            days_left = (obj.warranty_until - today).days
            if days_left < 30:
                color = "danger"
            elif days_left < 90:
                color = "warning"
            else:
                color = "success"

            return format_html(
                '<span class="badge bg-{}">до {} ({} дн.)</span>',
                color, obj.warranty_until.strftime("%d.%m.%Y"), days_left
            )
        else:
            return format_html(
                '<span class="badge bg-dark">истекла {}</span>',
                obj.warranty_until.strftime("%d.%m.%Y")
            )

    @admin.display(description=_("Действия"))
    def actions(self, obj):
        view_url = reverse("assets:asset_detail", args=[obj.pk])
        return format_html(
            '<a href="{}" class="btn btn-sm btn-outline-info" target="_blank">'
            '<i class="fas fa-eye"></i></a>',
            view_url
        )

    @admin.display(description=_("Последнее изменение"))
    def last_change(self, obj):
        h = obj.history.first()
        if not h:
            return "—"

        user = h.history_user
        username = user.username if user else "system"

        return format_html(
            '{}<br><small class="text-muted">{}</small>',
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            username
        )

    @admin.display(description=_("Превью фото"))
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px;" />',
                obj.photo.url
            )
        return _("Фото отсутствует")

    @admin.display(description=_("Возраст"))
    def age_display(self, obj):
        age = obj.age_in_years
        if age is None:
            return _("Не указана дата ввода")
        return _("{} лет").format(age)

    @admin.display(description=_("Статус гарантии"))
    def warranty_status(self, obj):
        if obj.is_under_warranty:
            return format_html(
                '<span class="badge bg-success">{}</span>',
                _("Действует")
            )
        elif obj.warranty_until:
            return format_html(
                '<span class="badge bg-dark">{}</span>',
                _("Истекла")
            )
        return _("Не указана")

    # =========================
    # ACTIONS
    # =========================
    actions = [
        'mark_as_archived',
        'mark_as_active',
        'export_to_csv',
    ]

    @admin.action(description=_("Переместить в архив"))
    def mark_as_archived(self, request, queryset):
        from core.audit import build_change_reason

        updated = queryset.update(
            global_state=WorkstationGlobalState.ARCHIVED,
            status=WorkstationStatus.DECOMMISSIONED
        )

        # Логируем изменения для каждого объекта
        for obj in queryset:
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "admin: массовое перемещение в архив"
            )
            obj.save()

        self.message_user(
            request,
            _("{} оборудований перемещено в архив").format(updated)
        )

    @admin.action(description=_("Вернуть в эксплуатацию"))
    def mark_as_active(self, request, queryset):
        from core.audit import build_change_reason

        updated = queryset.update(
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD
        )

        for obj in queryset:
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "admin: массовый возврат в эксплуатацию"
            )
            obj.save()

        self.message_user(
            request,
            _("{} оборудований возвращено в эксплуатацию").format(updated)
        )

    @admin.action(description=_("Экспорт в CSV"))
    def export_to_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="workstations.csv"'

        writer = csv.writer(response, delimiter=';')
        writer.writerow([
            _("Название"),
            _("Категория"),
            _("Тип"),
            _("Производитель"),
            _("Модель"),
            _("Статус"),
            _("Локация"),
            _("Ответственный"),
            _("Серийный номер"),
            _("Инвентарный номер"),
        ])

        for obj in queryset:
            writer.writerow([
                obj.name,
                obj.get_category_display(),
                obj.type_name,
                obj.manufacturer,
                obj.model,
                obj.get_status_display(),
                str(obj.location),
                str(obj.responsible) if obj.responsible else "",
                obj.serial_number,
                obj.inventory_number,
            ])

        return response

    # =========================
    # CHANGELIST
    # =========================
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # Статистика для отображения
        stats = {
            'total': Workstation.objects.count(),
            'active': Workstation.objects.filter(
                global_state=WorkstationGlobalState.ACTIVE
            ).count(),
            'under_warranty': Workstation.objects.filter(
                warranty_until__gte=timezone.now().date()
            ).count(),
            'needs_repair': Workstation.objects.filter(
                status=WorkstationStatus.PROBLEM
            ).count(),
        }

        extra_context['stats'] = stats
        return super().changelist_view(request, extra_context)

    # =========================
    # FORM CUSTOMIZATION
    # =========================
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "responsible":
            # Используем HumanResource.objects.all() без select_related на user
            kwargs["queryset"] = db_field.remote_field.model.objects.all().order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Добавляем классы для полей дат
        if 'commissioning_date' in form.base_fields:
            form.base_fields['commissioning_date'].widget.attrs['class'] = 'datepicker'
        if 'warranty_until' in form.base_fields:
            form.base_fields['warranty_until'].widget.attrs['class'] = 'datepicker'

        return form

    class Media:
        css = {
            'all': ('admin/css/workstation.css',)
        }
        js = (
            'admin/js/datepicker.js',
        )