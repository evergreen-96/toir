from django.db.models import Q


class SearchUtils:
    """Утилиты для поиска"""

    @staticmethod
    def search_materials(queryset, query):
        """Поиск материалов по нескольким полям"""
        return queryset.filter(
            Q(name__icontains=query) |
            Q(group__icontains=query) |
            Q(article__icontains=query) |
            Q(part_number__icontains=query) |
            Q(vendor__icontains=query)
        )

    @staticmethod
    def search_warehouses(queryset, query):
        """Поиск складов по нескольким полям"""
        return queryset.filter(
            Q(name__icontains=query) |
            Q(location__name__icontains=query) |
            Q(responsible__name__icontains=query)
        )


class ValidationUtils:
    """Утилиты для валидации"""

    # @staticmethod
    # def validate_quantity(available, reserved):
    #     """Проверка корректности количеств"""
    #     if reserved > available:
    #         return False, "Резерв не может превышать доступное количество"
    #     return True, ""

    @staticmethod
    def validate_positive_number(value, field_name="Значение"):
        """Проверка, что число положительное"""
        if value < 0:
            return False, f"{field_name} не может быть отрицательным"
        return True, ""