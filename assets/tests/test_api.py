from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission

from assets.models import Workstation, WorkstationCategory, WorkstationStatus
from locations.models import Location
from hr.models import HumanResource


class WorkstationAPITest(TestCase):
    """Тесты для REST API оборудования"""

    def setUp(self):
        # Создаем пользователя с правами
        self.user = User.objects.create_user(
            username='api_user',
            password='testpass123',
            email='api@example.com'
        )

        # Добавляем разрешение на просмотр оборудования
        view_perm = Permission.objects.get(codename='view_workstation')
        self.user.user_permissions.add(view_perm)

        self.client.force_login(self.user)

        # Создаем тестовые данные
        self.location = Location.objects.create(name="API цех")
        self.hr = HumanResource.objects.create(
            name="API Ответственный",
            job_title="API Тестер"
        )

        # Создаем тестовое оборудование
        self.workstation = Workstation.objects.create(
            name='API Станок',
            category=WorkstationCategory.MAIN,
            type_name='API Станок',
            location=self.location,
            global_state='active',
            status=WorkstationStatus.PROD,
            inventory_number='API-001'
        )


class WorkstationJSONEndpointsTest(TestCase):
    """Тесты для JSON endpoints (не REST API)"""

    def setUp(self):
        from django.contrib.auth.models import User, Permission

        # Создаем пользователя с правами
        self.user = User.objects.create_user(
            username='apitest',
            password='testpass123',
            email='apitest@example.com'
        )

        # Добавляем разрешения на просмотр и изменение оборудования
        permissions = Permission.objects.filter(
            codename__in=['view_workstation', 'change_workstation']
        )
        self.user.user_permissions.add(*permissions)

        self.client.force_login(self.user)

        # Создаем тестовые данные
        self.location = Location.objects.create(name="JSON цех")
        self.workstation = Workstation.objects.create(
            name='JSON Станок',
            category=WorkstationCategory.MAIN,
            type_name='JSON',
            location=self.location,
            global_state='active',
            status=WorkstationStatus.PROD,
            inventory_number='JSON-001'
        )

    def test_json_response_structure(self):
        """Тест структуры JSON ответов"""
        # Тестируем AJAX endpoints из views.py

        # 1. Проверяем, что пользователь аутентифицирован
        self.assertTrue(self.user.is_authenticated)

        # 2. Проверяем, что у пользователя есть права
        self.assertTrue(self.user.has_perm('assets.view_workstation'))

        # 3. Делаем запрос к AJAX endpoint
        url = reverse('assets:ajax_get_info')
        response = self.client.get(url, {'id': self.workstation.pk})

        # 4. Отладочная информация при ошибке
        if response.status_code != 200:
            print(f"\n=== DEBUG INFO ===")
            print(f"URL: {url}")
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content: {response.content}")
            print(f"User: {self.user.username}")
            print(f"User permissions: {list(self.user.get_all_permissions())}")
            print(f"Workstation ID: {self.workstation.pk}")
            print(f"Workstation exists: {Workstation.objects.filter(pk=self.workstation.pk).exists()}")
            print("================\n")

        # 5. Проверяем статус ответа
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}. Check debug output above."
        )

        # 6. Проверяем, что это JSON
        self.assertEqual(
            response['Content-Type'],
            'application/json',
            f"Expected application/json, got {response['Content-Type']}"
        )

        # 7. Парсим JSON
        import json
        try:
            data = json.loads(response.content.decode('utf-8'))
        except json.JSONDecodeError as e:
            self.fail(f"Invalid JSON response: {e}\nResponse: {response.content}")

        # 8. Проверяем структуру ответа
        self.assertTrue(data['ok'], f"Response not ok: {data}")
        self.assertEqual(data['id'], self.workstation.pk)
        self.assertEqual(data['name'], 'JSON Станок')
        self.assertEqual(data['type_name'], 'JSON')
        self.assertEqual(data['category'], 'Основное')
        self.assertEqual(data['status'], 'Работает')
        self.assertEqual(data['location'], 'JSON цех')
        self.assertIsNone(data['responsible'])
        self.assertIsNone(data['photo_url'])
        self.assertIsNone(data['warranty_until'])
        self.assertFalse(data['is_under_warranty'])
        self.assertIsNone(data['age'])

    def test_ajax_endpoints_without_permission(self):
        """Тест AJAX endpoints без прав доступа"""
        # Создаем пользователя без прав
        user_no_perm = User.objects.create_user(
            username='noperm',
            password='testpass123'
        )
        self.client.force_login(user_no_perm)

        # Пытаемся получить информацию об оборудовании
        response = self.client.get(
            reverse('assets:ajax_get_info'),
            {'id': self.workstation.pk}
        )

        # Проверяем, что доступ запрещен (403 или редирект)
        self.assertIn(response.status_code, [302, 403])

    def test_ajax_endpoints_unauthenticated(self):
        """Тест AJAX endpoints без аутентификации"""
        self.client.logout()

        # Пытаемся получить информацию об оборудовании
        response = self.client.get(
            reverse('assets:ajax_get_info'),
            {'id': self.workstation.pk}
        )

        # Проверяем, что требуется аутентификация (302 - редирект на логин, или 403)
        self.assertIn(response.status_code, [302, 403])

    def test_ajax_get_info_invalid_id(self):
        """Тест AJAX endpoint с невалидным ID"""
        response = self.client.get(
            reverse('assets:ajax_get_info'),
            {'id': 99999}  # Несуществующий ID
        )

        # Проверяем, что возвращается ошибка 404
        self.assertEqual(response.status_code, 404)

        # Проверяем структуру JSON ошибки
        import json
        data = json.loads(response.content.decode('utf-8'))
        self.assertFalse(data['ok'])
        self.assertIn('error', data)

    def test_ajax_get_info_missing_id(self):
        """Тест AJAX endpoint без ID"""
        response = self.client.get(reverse('assets:ajax_get_info'))

        # Проверяем, что возвращается ошибка 400
        self.assertEqual(response.status_code, 400)

        # Проверяем структуру JSON ошибки
        import json
        data = json.loads(response.content.decode('utf-8'))
        self.assertFalse(data['ok'])
        self.assertIn('error', data)
        self.assertIn('Не указан ID', data['error'])

    def test_ajax_status_endpoints(self):
        """Тест AJAX endpoints для работы со статусами"""
        # 1. Получаем текущий статус
        response = self.client.get(
            reverse('assets:ajax_get_status'),
            {'id': self.workstation.pk}
        )
        self.assertEqual(response.status_code, 200)

        import json
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['ok'])
        self.assertEqual(data['current'], WorkstationStatus.PROD)
        self.assertEqual(data['current_display'], 'Работает')
        self.assertIn('choices', data)
        self.assertTrue(data['can_change'])

        # 2. Меняем статус
        response = self.client.post(
            reverse('assets:ajax_update_status'),
            {
                'id': self.workstation.pk,
                'status': WorkstationStatus.MAINT,
            }
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(data['ok'])
        self.assertEqual(data['new_status'], WorkstationStatus.MAINT)
        self.assertEqual(data['new_status_display'], 'Техническое обслуживание')

        # 3. Проверяем, что статус изменился в базе
        self.workstation.refresh_from_db()
        self.assertEqual(self.workstation.status, WorkstationStatus.MAINT)

    def test_ajax_status_invalid_data(self):
        """Тест AJAX endpoints с невалидными данными"""
        # 1. Обновление с невалидным статусом
        response = self.client.post(
            reverse('assets:ajax_update_status'),
            {
                'id': self.workstation.pk,
                'status': 'invalid_status',
            }
        )
        self.assertEqual(response.status_code, 400)

        # 2. Получение статуса без ID
        response = self.client.get(reverse('assets:ajax_get_status'))
        self.assertEqual(response.status_code, 400)

    def test_multiple_ajax_calls(self):
        """Тест нескольких последовательных AJAX вызовов"""
        # Получаем информацию
        response1 = self.client.get(
            reverse('assets:ajax_get_info'),
            {'id': self.workstation.pk}
        )
        self.assertEqual(response1.status_code, 200)

        # Получаем статус
        response2 = self.client.get(
            reverse('assets:ajax_get_status'),
            {'id': self.workstation.pk}
        )
        self.assertEqual(response2.status_code, 200)

        # Меняем статус
        response3 = self.client.post(
            reverse('assets:ajax_update_status'),
            {
                'id': self.workstation.pk,
                'status': WorkstationStatus.PROBLEM,
            }
        )
        self.assertEqual(response3.status_code, 200)

        # Проверяем, что статус изменился
        self.workstation.refresh_from_db()
        self.assertEqual(self.workstation.status, WorkstationStatus.PROBLEM)

        # Получаем информацию снова
        response4 = self.client.get(
            reverse('assets:ajax_get_info'),
            {'id': self.workstation.pk}
        )
        self.assertEqual(response4.status_code, 200)

        import json
        data = json.loads(response4.content.decode('utf-8'))
        self.assertEqual(data['status'], 'Аварийный ремонт')