"""
Locations Admin
===============
"""

from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from core.admin_base import BaseHistoryAdmin
from .models import Location


@admin.register(Location)
class LocationAdmin(BaseHistoryAdmin):
    """Админка локаций."""

    list_display = (
        "id",
        "name",
        "display_parent",
        "display_responsible",
        "children_count",
        "last_change",
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "description", "parent__name", "responsible__name")
    list_filter = ("parent",)
    ordering = ("name",)
    readonly_fields = ("last_change", "children_list")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "parent", "responsible", "description")
        }),
        ("Дочерние локации", {
            "fields": ("children_list",),
            "classes": ("collapse",)
        }),
        ("История", {
            "fields": ("last_change",),
            "classes": ("collapse",)
        }),
    )

    @admin.display(description="Родитель")
    def display_parent(self, obj):
        if obj.parent:
            return format_html(
                '<a href="{}">{}</a>',
                f"/admin/locations/location/{obj.parent.pk}/change/",
                obj.parent.name
            )
        return format_html('<span class="text-muted">—</span>')

    @admin.display(description="Ответственный")
    def display_responsible(self, obj):
        return obj.responsible.name if obj.responsible else "—"

    @admin.display(description="Дочерних")
    def children_count(self, obj):
        count = Location.objects.filter(parent=obj).count()
        if count > 0:
            return format_html('<span class="badge bg-info">{}</span>', count)
        return format_html('<span class="text-muted">0</span>')

    @admin.display(description="Дочерние локации")
    def children_list(self, obj):
        children = Location.objects.filter(parent=obj).order_by("name")
        if not children:
            return "Нет дочерних локаций"

        items = []
        for child in children[:20]:  # Лимит 20
            items.append(f'<li><a href="/admin/locations/location/{child.pk}/change/">{child.name}</a></li>')

        html = f'<ul>{"".join(items)}</ul>'
        if children.count() > 20:
            html += f'<p class="text-muted">... и ещё {children.count() - 20}</p>'

        return format_html(html)