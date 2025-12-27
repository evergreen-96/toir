from django.db.models import Q


def get_stock_status(qty_available, qty_reserved=0, min_stock=0, is_active=True):
    """Определяет статус запаса материала"""
    if not is_active:
        return 'inactive'
    elif qty_available == 0:
        return 'out_of_stock'
    elif qty_available <= min_stock:
        return 'low_stock'
    elif qty_available <= qty_reserved:
        return 'reserved'
    else:
        return 'in_stock'


def format_quantity(quantity, uom='pcs'):
    """Форматирует количество с единицами измерения"""
    uom_display = {
        'pcs': 'шт',
        'kg': 'кг',
        'l': 'л',
        'm': 'м',
        'h': 'ч',
        'set': 'комплект',
        'roll': 'рулон',
        'box': 'коробка',
        'pal': 'паллет',
    }

    uom_text = uom_display.get(uom, uom)

    # Для целых чисел не показываем дробную часть
    if quantity.is_integer():
        return f"{int(quantity)} {uom_text}"
    else:
        return f"{quantity:.2f} {uom_text}"


def search_materials(queryset, query):
    """Поиск материалов по нескольким полям"""
    return queryset.filter(
        Q(name__icontains=query) |
        Q(group__icontains=query) |
        Q(article__icontains=query) |
        Q(part_number__icontains=query) |
        Q(vendor__icontains=query)
    )


def search_warehouses(queryset, query):
    """Поиск складов по нескольким полям"""
    return queryset.filter(
        Q(name__icontains=query) |
        Q(location__name__icontains=query) |
        Q(responsible__name__icontains=query)
    )