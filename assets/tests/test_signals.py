# [file name]: test_signals.py
# [file content begin]
from django.test import TestCase
from django.utils import timezone
import logging

from assets.models import Workstation, WorkstationCategory, WorkstationStatus, WorkstationGlobalState
from locations.models import Location


class WorkstationSignalsTest(TestCase):
    """Тесты сигналов оборудования"""

    def setUp(self):
        self.location = Location.objects.create(name="Сигнальный цех")

        # Настраиваем логирование для тестирования
        self.logger = logging.getLogger('assets.signals')
        self.log_capture = []

        class TestHandler(logging.Handler):
            def __init__(self, log_capture):
                super().__init__()
                self.log_capture = log_capture

            def emit(self, record):
                self.log_capture.append(record.getMessage())

        self.handler = TestHandler(self.log_capture)
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_status_change_logging(self):
        """Тест логирования изменения статуса"""
        workstation = Workstation.objects.create(
            name='Сигнальный станок',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
        )

        # Меняем статус
        workstation.status = WorkstationStatus.MAINT
        workstation.save()

        # Проверяем логи
        log_messages = '\n'.join(self.log_capture)
        self.assertIn('Статус оборудования', log_messages)
        self.assertIn('Работает', log_messages)
        self.assertIn('Техническое обслуживание', log_messages)

    def test_location_change_logging(self):
        """Тест логирования изменения локации"""
        location2 = Location.objects.create(name="Новый цех")

        workstation = Workstation.objects.create(
            name='Перемещаемый станок',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
        )

        # Меняем локацию
        workstation.location = location2
        workstation.save()

        # Проверяем логи
        log_messages = '\n'.join(self.log_capture)
        self.assertIn('Локация оборудования', log_messages)

    def test_creation_logging(self):
        """Тест логирования создания"""
        # Создаем объект - сигнал должен сработать
        workstation = Workstation.objects.create(
            name='Новый станок для логов',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
        )

        # Проверяем логи создания
        log_messages = '\n'.join(self.log_capture)
        self.assertIn('Создано новое оборудование', log_messages)
        self.assertIn('Новый станок для логов', log_messages)

    def test_update_logging(self):
        """Тест логирования обновления"""
        workstation = Workstation.objects.create(
            name='Станок для обновления',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
        )

        # Обновляем
        workstation.name = 'Обновленный станок'
        workstation.save()

        # Проверяем логи обновления
        log_messages = '\n'.join(self.log_capture)
        self.assertIn('Обновлено оборудование', log_messages)
# [file content end]