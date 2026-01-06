"""
core/templatetags/core_tags.py

Общие template tags для использования во всех шаблонах.
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from core.constants import (
    STATUS_COLORS,
    STATUS_BADGE_CLASSES,
    PRIORITY_COLORS,
    PRIORITY_ICONS,
    get_status_color,
    get_status_badge_class,
    get_priority_color,
    get_priority_icon,
)

register = template.Library()


# =============================================================================
# БЕЙДЖИ СТАТУСОВ
# =============================================================================

@register.simple_tag
def status_badge(status, display=None, size=''):
    """
    Отображает статус в виде Bootstrap бейджа.
    
    Использование:
        {% status_badge object.status %}
        {% status_badge object.status object.get_status_display %}
        {% status_badge object.status size="sm" %}
    """
    if not status:
        return mark_safe('<span class="badge bg-secondary">—</span>')
    
    badge_class = get_status_badge_class(status)
    display_text = display or status
    size_class = f'badge-{size}' if size else ''
    
    return format_html(
        '<span class="badge {} {}">{}</span>',
        badge_class,
        size_class,
        display_text,
    )


@register.simple_tag
def priority_badge(priority, display=None):
    """
    Отображает приоритет в виде бейджа с иконкой.
    
    Использование:
        {% priority_badge object.priority %}
        {% priority_badge object.priority object.get_priority_display %}
    """
    if not priority:
        return mark_safe('<span class="badge bg-secondary">—</span>')
    
    color = get_priority_color(priority)
    icon = get_priority_icon(priority)
    display_text = display or priority
    
    return format_html(
        '<span class="badge" style="background-color: {};">'
        '<i class="{} me-1"></i>{}</span>',
        color,
        icon,
        display_text,
    )


@register.simple_tag
def bool_badge(value, true_text='Да', false_text='Нет'):
    """
    Отображает булево значение в виде бейджа.
    
    Использование:
        {% bool_badge object.is_active %}
        {% bool_badge object.is_active "Активен" "Неактивен" %}
    """
    if value:
        return format_html(
            '<span class="badge bg-success">{}</span>',
            true_text,
        )
    else:
        return format_html(
            '<span class="badge bg-secondary">{}</span>',
            false_text,
        )


# =============================================================================
# ФОРМАТИРОВАНИЕ
# =============================================================================

@register.filter
def format_date(value, format_str='%d.%m.%Y'):
    """
    Форматирует дату.
    
    Использование:
        {{ object.created_at|format_date }}
        {{ object.created_at|format_date:"%d/%m/%Y" }}
    """
    if not value:
        return '—'
    try:
        return value.strftime(format_str)
    except (AttributeError, ValueError):
        return str(value)


@register.filter
def format_datetime(value, format_str='%d.%m.%Y %H:%M'):
    """
    Форматирует дату и время.
    
    Использование:
        {{ object.created_at|format_datetime }}
    """
    return format_date(value, format_str)


@register.filter
def format_number(value, decimals=2):
    """
    Форматирует число с разделителями.
    
    Использование:
        {{ object.amount|format_number }}
        {{ object.amount|format_number:0 }}
    """
    if value is None:
        return '—'
    try:
        formatted = f'{float(value):,.{decimals}f}'
        # Заменяем запятую на пробел (русский формат)
        return formatted.replace(',', ' ')
    except (ValueError, TypeError):
        return str(value)


@register.filter
def default_dash(value):
    """
    Возвращает тире если значение пустое.
    
    Использование:
        {{ object.description|default_dash }}
    """
    if value is None or value == '':
        return '—'
    return value


# =============================================================================
# ИКОНКИ И UI
# =============================================================================

@register.simple_tag
def icon(name, size='', extra_class=''):
    """
    Отображает Bootstrap Icon.
    
    Использование:
        {% icon "check" %}
        {% icon "gear" size="lg" %}
        {% icon "person" extra_class="text-primary" %}
    """
    classes = [f'bi-{name}']
    if size:
        classes.append(f'bi-{size}')
    if extra_class:
        classes.append(extra_class)
    
    return format_html('<i class="bi {}"></i>', ' '.join(classes))


@register.simple_tag
def empty_state(message='Данные отсутствуют', icon_name='inbox'):
    """
    Отображает пустое состояние.
    
    Использование:
        {% empty_state %}
        {% empty_state "Нет записей" "search" %}
    """
    return format_html(
        '<div class="text-center text-muted py-5">'
        '<i class="bi bi-{} display-4"></i>'
        '<p class="mt-3">{}</p>'
        '</div>',
        icon_name,
        message,
    )


@register.simple_tag
def loading_spinner(text='Загрузка...'):
    """
    Отображает индикатор загрузки.
    
    Использование:
        {% loading_spinner %}
        {% loading_spinner "Обработка..." %}
    """
    return format_html(
        '<div class="d-flex align-items-center">'
        '<div class="spinner-border spinner-border-sm me-2" role="status"></div>'
        '<span>{}</span>'
        '</div>',
        text,
    )


# =============================================================================
# ПАГИНАЦИЯ
# =============================================================================

@register.inclusion_tag('core/partials/pagination.html', takes_context=True)
def pagination(context, page_obj, adjacent_pages=2):
    """
    Отображает пагинацию.
    
    Использование:
        {% pagination page_obj %}
        {% pagination page_obj adjacent_pages=3 %}
    """
    current_page = page_obj.number
    total_pages = page_obj.paginator.num_pages
    
    # Вычисляем диапазон страниц для отображения
    start_page = max(1, current_page - adjacent_pages)
    end_page = min(total_pages, current_page + adjacent_pages)
    
    page_range = range(start_page, end_page + 1)
    
    return {
        'page_obj': page_obj,
        'page_range': page_range,
        'show_first': start_page > 1,
        'show_last': end_page < total_pages,
        'request': context.get('request'),
    }


# =============================================================================
# ФОРМЫ
# =============================================================================

@register.filter
def add_class(field, css_class):
    """
    Добавляет CSS класс к полю формы.
    
    Использование:
        {{ form.name|add_class:"form-control-lg" }}
    """
    existing_class = field.field.widget.attrs.get('class', '')
    field.field.widget.attrs['class'] = f'{existing_class} {css_class}'.strip()
    return field


@register.filter
def add_attr(field, attr_value):
    """
    Добавляет атрибут к полю формы.
    
    Использование:
        {{ form.name|add_attr:"placeholder:Введите имя" }}
        {{ form.email|add_attr:"autofocus" }}
    """
    if ':' in attr_value:
        attr, value = attr_value.split(':', 1)
    else:
        attr, value = attr_value, True
    
    field.field.widget.attrs[attr] = value
    return field


@register.simple_tag
def form_errors(form):
    """
    Отображает ошибки формы в виде alert.
    
    Использование:
        {% form_errors form %}
    """
    if not form.errors:
        return ''
    
    errors_html = []
    
    # Non-field errors
    for error in form.non_field_errors():
        errors_html.append(f'<li>{error}</li>')
    
    # Field errors
    for field_name, errors in form.errors.items():
        if field_name != '__all__':
            field_label = form.fields.get(field_name)
            label = field_label.label if field_label else field_name
            for error in errors:
                errors_html.append(f'<li><strong>{label}:</strong> {error}</li>')
    
    if not errors_html:
        return ''
    
    return format_html(
        '<div class="alert alert-danger">'
        '<ul class="mb-0">{}</ul>'
        '</div>',
        mark_safe(''.join(errors_html)),
    )


# =============================================================================
# РАЗРЕШЕНИЯ
# =============================================================================

@register.simple_tag(takes_context=True)
def has_perm(context, perm):
    """
    Проверяет разрешение пользователя.
    
    Использование:
        {% has_perm "app.add_model" as can_add %}
        {% if can_add %}...{% endif %}
    """
    request = context.get('request')
    if request and hasattr(request, 'user'):
        return request.user.has_perm(perm)
    return False
