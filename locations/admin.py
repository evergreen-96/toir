from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Location


@admin.register(Location)
class LocationAdmin(SimpleHistoryAdmin):
    list_display = ("name", "parent", "responsible")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение локации"
        else:
            obj._change_reason = "admin: создание локации"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
