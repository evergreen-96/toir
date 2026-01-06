"""
core/constants.py

Общие константы, используемые в разных приложениях.
"""

from django.db import models


# =============================================================================
# ЦВЕТА ДЛЯ СТАТУСОВ
# =============================================================================

STATUS_COLORS = {
    # Общие
    'new': '#6c757d',           # gray
    'active': '#28a745',        # green
    'inactive': '#dc3545',      # red
    'pending': '#ffc107',       # yellow
    'completed': '#28a745',     # green
    'cancelled': '#dc3545',     # red
    
    # WorkOrder
    'in_progress': '#007bff',   # blue
    'done': '#28a745',          # green
    'failed': '#dc3545',        # red
    
    # Workstation
    'prod': '#28a745',          # green - работает
    'maint': '#ffc107',         # yellow - ТО
    'setup': '#17a2b8',         # cyan - наладка
    'problem': '#dc3545',       # red - авария
    'decommissioned': '#6c757d', # gray - выведено
    
    # Material stock
    'in_stock': '#28a745',      # green
    'low_stock': '#ffc107',     # yellow
    'out_of_stock': '#dc3545',  # red
    'reserved': '#17a2b8',      # cyan
}

# Bootstrap классы для бейджей
STATUS_BADGE_CLASSES = {
    'new': 'bg-secondary',
    'active': 'bg-success',
    'inactive': 'bg-danger',
    'pending': 'bg-warning text-dark',
    'in_progress': 'bg-primary',
    'done': 'bg-success',
    'failed': 'bg-danger',
    'cancelled': 'bg-dark',
    'prod': 'bg-success',
    'maint': 'bg-warning text-dark',
    'setup': 'bg-info',
    'problem': 'bg-danger',
    'in_stock': 'bg-success',
    'low_stock': 'bg-warning text-dark',
    'out_of_stock': 'bg-danger',
}


# =============================================================================
# ПРИОРИТЕТЫ
# =============================================================================

class Priority(models.TextChoices):
    """Общие приоритеты для разных моделей."""
    LOW = 'low', 'Низкий'
    MED = 'med', 'Средний'
    HIGH = 'high', 'Высокий'
    CRITICAL = 'critical', 'Критический'


PRIORITY_COLORS = {
    'low': '#28a745',      # green
    'med': '#ffc107',      # yellow
    'high': '#fd7e14',     # orange
    'critical': '#dc3545', # red
}

PRIORITY_ICONS = {
    'low': 'bi-arrow-down',
    'med': 'bi-dash',
    'high': 'bi-arrow-up',
    'critical': 'bi-exclamation-triangle-fill',
}


# =============================================================================
# ЕДИНИЦЫ ИЗМЕРЕНИЯ
# =============================================================================

class UnitOfMeasure(models.TextChoices):
    """Единицы измерения."""
    PCS = 'pcs', 'шт'
    KG = 'kg', 'кг'
    G = 'g', 'г'
    L = 'l', 'л'
    ML = 'ml', 'мл'
    M = 'm', 'м'
    CM = 'cm', 'см'
    MM = 'mm', 'мм'
    M2 = 'm2', 'м²'
    M3 = 'm3', 'м³'
    H = 'h', 'ч'
    MIN = 'min', 'мин'
    SET = 'set', 'комплект'
    ROLL = 'roll', 'рулон'
    BOX = 'box', 'коробка'
    PAL = 'pal', 'паллет'


# =============================================================================
# ИНТЕРВАЛЫ ВРЕМЕНИ
# =============================================================================

class IntervalUnit(models.TextChoices):
    """Единицы измерения интервалов."""
    MINUTE = 'minute', 'Минута'
    HOUR = 'hour', 'Час'
    DAY = 'day', 'День'
    WEEK = 'week', 'Неделя'
    MONTH = 'month', 'Месяц'
    YEAR = 'year', 'Год'


# =============================================================================
# ПАГИНАЦИЯ
# =============================================================================

DEFAULT_PAGE_SIZE = 20
PAGE_SIZE_OPTIONS = [10, 20, 50, 100]


# =============================================================================
# ЛИМИТЫ ЗАГРУЗКИ ФАЙЛОВ
# =============================================================================

MAX_FILE_SIZE_MB = 10
MAX_IMAGE_SIZE_MB = 5
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv']


# =============================================================================
# ФОРМАТЫ ДАТЕ/ВРЕМЕНИ
# =============================================================================

DATE_FORMAT = '%d.%m.%Y'
DATETIME_FORMAT = '%d.%m.%Y %H:%M'
TIME_FORMAT = '%H:%M'

DATE_FORMAT_INPUT = '%Y-%m-%d'
DATETIME_FORMAT_INPUT = '%Y-%m-%dT%H:%M'


# =============================================================================
# УТИЛИТЫ
# =============================================================================

def get_status_color(status: str, default: str = '#000000') -> str:
    """Возвращает цвет для статуса."""
    return STATUS_COLORS.get(status, default)


def get_status_badge_class(status: str, default: str = 'bg-secondary') -> str:
    """Возвращает Bootstrap класс бейджа для статуса."""
    return STATUS_BADGE_CLASSES.get(status, default)


def get_priority_color(priority: str, default: str = '#6c757d') -> str:
    """Возвращает цвет для приоритета."""
    return PRIORITY_COLORS.get(priority, default)


def get_priority_icon(priority: str, default: str = 'bi-dash') -> str:
    """Возвращает иконку для приоритета."""
    return PRIORITY_ICONS.get(priority, default)
