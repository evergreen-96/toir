from django.contrib import admin
from .models import HumanResource

@admin.register(HumanResource)
class HumanResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title", "manager")
    search_fields = ("name", "job_title")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "manager" and request.resolver_match and request.resolver_match.kwargs.get("object_id"):
            # исключаем самого себя из выбора начальника
            obj_id = request.resolver_match.kwargs["object_id"]
            kwargs["queryset"] = HumanResource.objects.exclude(pk=obj_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)