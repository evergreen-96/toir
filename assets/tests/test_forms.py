from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile


from assets.models import Workstation, WorkstationCategory, WorkstationStatus, WorkstationGlobalState
from assets.views import WorkstationForm
from locations.models import Location
from hr.models import HumanResource


class WorkstationFormTest(TestCase):
    """Тесты формы WorkstationForm"""

    def setUp(self):
        self.location = Location.objects.create(name="Цех №1")
        self.responsible = HumanResource.objects.create(
            name="Петров Петр Петрович",
            job_title="Технолог"
        )

        self.valid_data = {
            'name': 'Фрезерный станок',
            'category': WorkstationCategory.MAIN,
            'type_name': 'Фрезерный станок с ЧПУ',
            'global_state': WorkstationGlobalState.ACTIVE,
            'status': WorkstationStatus.PROD,
            'location': self.location.pk,
        }

    def test_valid_form(self):
        """Тест валидной формы"""
        form = WorkstationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Тест формы с отсутствующими обязательными полями"""
        # Удаляем обязательное поле
        invalid_data = self.valid_data.copy()
        del invalid_data['name']

        form = WorkstationForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_form_with_optional_fields(self):
        """Тест формы с опциональными полями"""
        data = self.valid_data.copy()
        data.update({
            'manufacturer': 'Haas',
            'model': 'VF-2',
            'serial_number': 'SN789012',
            'inventory_number': 'INV-002',
            'responsible': self.responsible.pk,
            'description': 'Фрезерный станок для обработки алюминия',
        })

        form = WorkstationForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_with_dates(self):
        """Тест формы с датами"""
        from django.utils import timezone

        data = self.valid_data.copy()
        commissioning_date = timezone.now().date()
        warranty_until = commissioning_date.replace(year=commissioning_date.year + 2)

        data.update({
            'commissioning_date': commissioning_date,
            'warranty_until': warranty_until,
        })

        form = WorkstationForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_invalid_dates(self):
        """Тест формы с невалидными датами"""
        from django.utils import timezone

        data = self.valid_data.copy()
        commissioning_date = timezone.now().date()
        warranty_until = commissioning_date.replace(year=commissioning_date.year - 1)  # Гарантия раньше ввода

        data.update({
            'commissioning_date': commissioning_date,
            'warranty_until': warranty_until,
        })

        form = WorkstationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('warranty_until', form.errors)

    def test_form_archived_state_with_wrong_status(self):
        """Тест формы: архивное состояние с неправильным статусом"""
        data = self.valid_data.copy()
        data['global_state'] = WorkstationGlobalState.ARCHIVED
        data['status'] = WorkstationStatus.PROD  # Должен быть DECOMMISSIONED

        form = WorkstationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)

    def test_form_unique_inventory_number(self):
        """Тест уникальности инвентарного номера"""
        # Создаем первое оборудование
        Workstation.objects.create(
            name='Станок 1',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
            inventory_number='INV-001'
        )

        # Пытаемся создать форму с таким же инвентарным номером
        data = self.valid_data.copy()
        data['inventory_number'] = 'INV-001'

        form = WorkstationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('inventory_number', form.errors)

    def test_form_photo_upload(self):
        """Тест загрузки фото"""
        from io import BytesIO
        from PIL import Image

        # Создаем тестовое изображение
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, 'JPEG')
        image_io.seek(0)

        photo = SimpleUploadedFile(
            'test.jpg',
            image_io.getvalue(),
            content_type='image/jpeg'
        )

        form_data = self.valid_data.copy()
        form_files = {'photo': photo}

        form = WorkstationForm(data=form_data, files=form_files)
        self.assertTrue(form.is_valid())

    def test_form_update_existing_object(self):
        """Тест формы для обновления существующего объекта"""
        # Создаем оборудование
        workstation = Workstation.objects.create(
            name='Старый станок',
            category=WorkstationCategory.MAIN,
            type_name='Станок',
            location=self.location,
            global_state=WorkstationGlobalState.ACTIVE,
            status=WorkstationStatus.PROD,
            inventory_number='INV-001'
        )

        # Обновляем через форму
        updated_data = self.valid_data.copy()
        updated_data.update({
            'name': 'Обновленный станок',
            'inventory_number': 'INV-001',  # Тот же инвентарный номер
        })

        form = WorkstationForm(data=updated_data, instance=workstation)
        self.assertTrue(form.is_valid())

        # Сохраняем
        updated_workstation = form.save()
        self.assertEqual(updated_workstation.name, 'Обновленный станок')
        self.assertEqual(updated_workstation.inventory_number, 'INV-001')

    def test_form_clean_method(self):
        """Тест кастомного метода clean формы"""
        form = WorkstationForm(data=self.valid_data)
        self.assertTrue(form.is_valid())

        # Проверяем, что clean не добавляет ошибок для валидных данных
        self.assertEqual(len(form.errors), 0)

    def test_form_field_widgets(self):
        """Тест виджетов полей формы"""
        form = WorkstationForm()

        # Проверяем, что поля дат используют правильный виджет
        self.assertEqual(form.fields['commissioning_date'].widget.input_type, 'date')
        self.assertEqual(form.fields['warranty_until'].widget.input_type, 'date')

        # Проверяем, что поле описания имеет textarea
        self.assertEqual(form.fields['description'].widget.__class__.__name__, 'Textarea')

        # Проверяем, что поле фото имеет правильные атрибуты
        self.assertEqual(form.fields['photo'].widget.attrs.get('accept'), 'image/*')

    def test_form_help_texts(self):
        """Тест вспомогательных текстов формы"""
        form = WorkstationForm()

        self.assertIn('Уникальный инвентарный номер', form.fields['inventory_number'].help_text)
        self.assertIn('Серийный номер от производителя', form.fields['serial_number'].help_text)
        self.assertIn('Рекомендуемый размер: 800x600px', form.fields['photo'].help_text)