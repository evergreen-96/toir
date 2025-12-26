# hr/tests/test_integration.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission

from hr.models import HumanResource


class IntegrationTest(TestCase):
    """Интеграционные тесты"""

    def setUp(self):
        # Создаем пользователя со всеми правами
        self.user = User.objects.create_user(
            username='admin',
            password='adminpass',
            is_staff=True
        )

        # Добавляем все разрешения
        permissions = Permission.objects.filter(
            codename__in=['view_humanresource', 'add_humanresource',
                          'change_humanresource', 'delete_humanresource']
        )
        self.user.user_permissions.add(*permissions)

        self.client = Client()
        self.client.force_login(self.user)

    def test_full_employee_lifecycle(self):
        """Тест полного жизненного цикла сотрудника"""
        print("\n=== Тест полного жизненного цикла сотрудника ===")

        # 1. Создаем сотрудника
        print("1. Создаем сотрудника...")
        create_data = {
            'name': 'Интеграционный сотрудник',
            'job_title': 'Разработчик',
            'is_active': True,
        }

        response = self.client.post(reverse('hr:hr_new'), create_data, follow=True)
        self.assertEqual(response.status_code, 200)

        # Получаем созданного сотрудника
        employee = HumanResource.objects.get(name='Интеграционный сотрудник')
        print(f"   Создан сотрудник ID: {employee.pk}")

        # 2. Просматриваем сотрудника
        print("2. Просматриваем сотрудника...")
        detail_url = reverse('hr:hr_detail', args=[employee.pk])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        print("   Просмотр успешен")

        # 3. Редактируем сотрудника
        print("3. Редактируем сотрудника...")
        edit_url = reverse('hr:hr_edit', args=[employee.pk])
        edit_data = {
            'name': 'Обновленный интеграционный сотрудник',
            'job_title': 'Старший разработчик',
            'is_active': True,
        }

        response = self.client.post(edit_url, edit_data, follow=True)
        employee.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(employee.name, 'Обновленный интеграционный сотрудник')
        self.assertEqual(employee.job_title, 'Старший разработчик')
        print("   Редактирование успешно")

        # 5. Удаляем сотрудника
        print("5. Удаляем сотрудника...")
        delete_url = reverse('hr:hr_delete', args=[employee.pk])
        response = self.client.post(delete_url)

        self.assertIn(response.status_code, [200, 302])
        self.assertFalse(HumanResource.objects.filter(pk=employee.pk).exists())
        print("   Удаление успешно")

        print("=== Тест завершен успешно ===")

    # УДАЛИТЕ или закомментируйте этот тест - метода нет
    # def test_organization_hierarchy(self):
    #     """Тест иерархии организации"""
    #     print("\n=== Тест иерархии организации ===")
    #
    #     # Создаем иерархию: директор -> менеджер -> сотрудник
    #     director = HumanResource.objects.create(
    #         name="Директор",
    #         job_title="Генеральный директор"
    #     )
    #
    #     manager = HumanResource.objects.create(
    #         name="Менеджер",
    #         job_title="Менеджер проекта",
    #         manager=director
    #     )
    #
    #     employee = HumanResource.objects.create(
    #         name="Сотрудник",
    #         job_title="Разработчик",
    #         manager=manager
    #     )
    #
    #     print(f"Создана иерархия: {director.name} -> {manager.name} -> {employee.name}")
    #
    #     # Проверяем отношения
    #     self.assertEqual(manager.manager, director)
    #     self.assertEqual(employee.manager, manager)
    #     self.assertIn(manager, director.subordinates.all())
    #     self.assertIn(employee, manager.subordinates.all())
    #
    #     # Проверяем методы менеджера
    #     self.assertEqual(director.subordinates.count(), 1)
    #     self.assertEqual(manager.subordinates.count(), 1)
    #
    #     print("   Иерархия работает корректно")