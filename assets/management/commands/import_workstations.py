import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from assets.models import Workstation, WorkstationCategory, WorkstationStatus, WorkstationGlobalState
from locations.models import Location
from hr.models import HumanResource


class Command(BaseCommand):
    help = 'Импорт оборудования из CSV файла'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Путь к CSV файлу')
        parser.add_argument(
            '--delimiter',
            default=';',
            help='Разделитель в CSV файле (по умолчанию ";")'
        )
        parser.add_argument(
            '--encoding',
            default='utf-8',
            help='Кодировка файла (по умолчанию "utf-8")'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновлять существующие записи'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый запуск без сохранения'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        delimiter = options['delimiter']
        encoding = options['encoding']
        update_existing = options['update']
        dry_run = options['dry_run']

        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter=delimiter)

                # Проверяем обязательные поля
                required_fields = ['name', 'type_name', 'location']
                for field in required_fields:
                    if field not in reader.fieldnames:
                        raise CommandError(f'Отсутствует обязательное поле: {field}')

                imported = 0
                updated = 0
                errors = []

                with transaction.atomic():
                    for i, row in enumerate(reader, 1):
                        try:
                            # Обработка строки
                            workstation = self.process_row(row, update_existing)

                            if not dry_run:
                                workstation.save()

                            if workstation.pk:
                                updated += 1
                            else:
                                imported += 1

                            if dry_run:
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'[DRY RUN] Обработана строка {i}: {workstation.name}'
                                    )
                                )

                        except Exception as e:
                            errors.append(f'Строка {i}: {str(e)}')
                            self.stdout.write(
                                self.style.ERROR(f'Ошибка в строке {i}: {str(e)}')
                            )
                            if not dry_run:
                                transaction.set_rollback(True)
                                break

                    if dry_run:
                        self.stdout.write(
                            self.style.SUCCESS(f'[DRY RUN] Импорт завершен: {imported} новых, {updated} обновлено'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'Импорт завершен: {imported} новых, {updated} обновлено'))

                        if errors:
                            self.stdout.write(self.style.WARNING('Были ошибки:'))
                            for error in errors:
                                self.stdout.write(self.style.ERROR(error))

        except FileNotFoundError:
            raise CommandError(f'Файл не найден: {csv_file}')
        except UnicodeDecodeError:
            raise CommandError(f'Неверная кодировка файла. Попробуйте --encoding windows-1251')
        except Exception as e:
            raise CommandError(f'Ошибка при обработке файла: {str(e)}')

    def process_row(self, row, update_existing):
        """Обработка одной строки CSV"""

        # Поиск существующего оборудования
        workstation = None
        inventory_number = row.get('inventory_number', '').strip()

        if inventory_number and update_existing:
            workstation = Workstation.objects.filter(
                inventory_number=inventory_number
            ).first()

        if not workstation:
            workstation = Workstation()

        # Основные поля
        workstation.name = row['name'].strip()
        workstation.type_name = row['type_name'].strip()

        # Категория
        category = row.get('category', '').strip()
        if category:
            workstation.category = self.get_category(category)

        # Статус
        status = row.get('status', '').strip()
        if status:
            workstation.status = self.get_status(status)

        # Глобальное состояние
        global_state = row.get('global_state', '').strip()
        if global_state:
            workstation.global_state = self.get_global_state(global_state)

        # Локация
        location_name = row['location'].strip()
        location = Location.objects.filter(name=location_name).first()
        if not location:
            raise ValueError(f'Локация не найдена: {location_name}')
        workstation.location = location

        # Ответственный
        responsible_name = row.get('responsible', '').strip()
        if responsible_name:
            responsible = HumanResource.objects.filter(
                user__username=responsible_name
            ).first()
            if responsible:
                workstation.responsible = responsible

        # Производитель и модель
        workstation.manufacturer = row.get('manufacturer', '').strip()
        workstation.model = row.get('model', '').strip()

        # Серийный и инвентарный номера
        workstation.serial_number = row.get('serial_number', '').strip()
        workstation.inventory_number = inventory_number

        # Даты
        commissioning_date = row.get('commissioning_date', '').strip()
        if commissioning_date:
            workstation.commissioning_date = self.parse_date(commissioning_date)

        warranty_until = row.get('warranty_until', '').strip()
        if warranty_until:
            workstation.warranty_until = self.parse_date(warranty_until)

        # Описание
        workstation.description = row.get('description', '').strip()

        return workstation

    def get_category(self, category_str):
        """Получение категории из строки"""
        category_map = {
            'Основное': WorkstationCategory.MAIN,
            'Вспомогательное': WorkstationCategory.AUX,
            'Контрольно-измерительное': WorkstationCategory.MEAS,
            'Испытательное': WorkstationCategory.TEST,
            'Другое': WorkstationCategory.OTHER,
        }
        return category_map.get(category_str, WorkstationCategory.MAIN)

    def get_status(self, status_str):
        """Получение статуса из строки"""
        status_map = {
            'Работает': WorkstationStatus.PROD,
            'Аварийный ремонт': WorkstationStatus.PROBLEM,
            'Техническое обслуживание': WorkstationStatus.MAINT,
            'Пусконаладочные работы': WorkstationStatus.SETUP,
            'В резерве': WorkstationStatus.RESERVED,
            'Выведено из эксплуатации': WorkstationStatus.DECOMMISSIONED,
        }
        return status_map.get(status_str, WorkstationStatus.PROD)

    def get_global_state(self, state_str):
        """Получение глобального состояния из строки"""
        state_map = {
            'Введено в эксплуатацию': WorkstationGlobalState.ACTIVE,
            'В архиве': WorkstationGlobalState.ARCHIVED,
            'Резерв': WorkstationGlobalState.RESERVE,
            'Выведено из эксплуатации': WorkstationGlobalState.DECOMMISSIONED,
        }
        return state_map.get(state_str, WorkstationGlobalState.ACTIVE)

    def parse_date(self, date_str):
        """Парсинг даты из различных форматов"""
        from datetime import datetime

        formats = [
            '%d.%m.%Y',
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        raise ValueError(f'Неверный формат даты: {date_str}')