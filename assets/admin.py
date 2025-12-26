from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from .models import Workstation


@admin.register(Workstation)
class WorkstationAdmin(SimpleHistoryAdmin):
    # ОСНОВНЫЕ НАСТРОЙКИ
    list_display = [
        'name',
        'category_display',
        'status_display',
        'get_location_name',
        'get_responsible_name',
        'get_warranty_status',
    ]

    list_filter = ['category', 'status', 'global_state', 'location']

    search_fields = ['name', 'inventory_number', 'serial_number', 'type_name']

    # ФОРМА
    fieldsets = [
        ('Основная информация', {
            'fields': ['name', 'category', 'type_name', 'photo']
        }),
        ('Детали', {
            'fields': ['manufacturer', 'model', 'serial_number', 'inventory_number']
        }),
        ('Состояние', {
            'fields': ['global_state', 'status', 'location', 'responsible']
        }),
        ('Эксплуатация', {
            'fields': ['commissioning_date', 'warranty_until', 'description']
        }),
    ]

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    # ПРОСТЫЕ МЕТОДЫ ДЛЯ ОТОБРАЖЕНИЯ

    @admin.display(description='Категория')
    def category_display(self, obj):
        return obj.get_category_display()

    @admin.display(description='Статус')
    def status_display(self, obj):
        return obj.get_status_display()

    def get_location_name(self, obj):
        return obj.location.name if obj.location else '-'

    get_location_name.short_description = 'Локация'
    get_location_name.admin_order_field = 'location__name'

    def get_responsible_name(self, obj):
        return str(obj.responsible) if obj.responsible else '-'

    get_responsible_name.short_description = 'Ответственный'

    def get_warranty_status(self, obj):
        if not obj.warranty_until:
            return 'Нет данных'

        from django.utils import timezone
        today = timezone.now().date()

        if obj.warranty_until >= today:
            days = (obj.warranty_until - today).days
            return f'Действует ({days} дн.)'
        else:
            return 'Истекла'

    get_warranty_status.short_description = 'Гарантия'

    # ПРОСТЫЕ ACTIONS
    actions = ['mark_as_archived_action', 'mark_as_active_action']

    def mark_as_archived_action(self, request, queryset):
        from .models import WorkstationGlobalState, WorkstationStatus
        queryset.update(
            global_state=WorkstationGlobalState.ARCHIVED,
            status=WorkstationStatus.DECOMMISSIONED
        )
        self.message_user(request, f'{queryset.count()} объектов перемещено в архив')

    mark_as_archived_action.short_description = 'Переместить в архив'

    def mark_as_active_action(self, request, queryset):
        from .models import WorkstationGlobalState, WorkstationStatus
        queryset.update(
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD
        )
        self.message_user(request, f'{queryset.count()} объектов активировано')

    mark_as_active_action.short_description = 'Активировать'