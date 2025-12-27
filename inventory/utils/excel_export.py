# inventory/utils/excel_export.py
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Font


def export_materials_to_excel(queryset, filename='materials.xlsx'):
    """Экспорт материалов в Excel"""
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Материалы'

    # Заголовки
    headers = ['ID', 'Название', 'Группа', 'Артикул', 'Количество', 'Склад']
    worksheet.append(headers)

    # Данные
    for material in queryset:
        worksheet.append([
            material.pk,
            material.name,
            material.group,
            material.article,
            material.qty_available,
            material.warehouse.name if material.warehouse else ''
        ])

    # Сохранение
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    workbook.save(response)

    return response


def export_warehouses_to_excel(queryset, filename='warehouses.xlsx'):
    """Экспорт складов в Excel"""
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Склады'

    # Заголовки
    headers = ['ID', 'Название', 'Локация', 'Ответственный']
    worksheet.append(headers)

    # Данные
    for warehouse in queryset:
        worksheet.append([
            warehouse.pk,
            warehouse.name,
            warehouse.location.name if warehouse.location else '',
            str(warehouse.responsible) if warehouse.responsible else ''
        ])

    # Сохранение
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    workbook.save(response)

    return response