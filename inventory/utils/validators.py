from django.core.exceptions import ValidationError


def validate_positive_number(value, field_name="Значение"):
    """Проверка, что число положительное"""
    if value < 0:
        raise ValidationError(f"{field_name} не может быть отрицательным")
    return value


def validate_stock_levels(available, reserved, min_stock=0):
    """Проверка корректности уровней запаса"""
    # if reserved > available:
    #     raise ValidationError("Резерв не может превышать доступное количество")

    if min_stock < 0:
        raise ValidationError("Минимальный запас не может быть отрицательным")

    return True