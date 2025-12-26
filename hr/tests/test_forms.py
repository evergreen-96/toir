import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.test import TestCase
from hr.forms import HumanResourceForm, HumanResourceSearchForm
from hr.models import HumanResource


class HumanResourceFormTest(TestCase):
    """Тесты форм"""

    def setUp(self):
        self.manager = HumanResource.objects.create(
            name="Руководитель Тест",
            job_title="Тестовый руководитель"
        )

        self.employee = HumanResource.objects.create(
            name="Сотрудник Тест",
            job_title="Тестовый сотрудник"
        )

    def test_human_resource_form_valid(self):
        """Тест валидной формы создания сотрудника"""
        from hr.forms import HumanResourceForm

        form_data = {
            'name': 'Новый сотрудник',
            'job_title': 'Разработчик',
            'is_active': True,
        }

        form = HumanResourceForm(data=form_data)
        self.assertTrue(form.is_valid())

        # Сохраняем
        hr = form.save()
        self.assertEqual(hr.name, 'Новый сотрудник')
        self.assertEqual(hr.job_title, 'Разработчик')
        self.assertTrue(hr.is_active)

    def test_human_resource_form_with_manager(self):
        """Тест формы с руководителем"""
        from hr.forms import HumanResourceForm

        form_data = {
            'name': 'Сотрудник с руководителем',
            'job_title': 'Аналитик',
            'manager': self.manager.pk,
            'is_active': True,
        }

        form = HumanResourceForm(data=form_data)
        self.assertTrue(form.is_valid())

        hr = form.save()
        self.assertEqual(hr.manager, self.manager)

    def test_human_resource_form_self_manager_exclusion(self):
        """Тест исключения самого себя из списка руководителей"""
        from hr.forms import HumanResourceForm

        # При редактировании существующего сотрудника
        form = HumanResourceForm(instance=self.employee)

        # Сотрудник не должен быть в списке возможных руководителей
        manager_queryset = form.fields['manager'].queryset
        self.assertNotIn(self.employee, manager_queryset)

    def test_human_resource_search_form(self):
        """Тест формы поиска"""
        from hr.forms import HumanResourceSearchForm

        # Создаем форму без данных
        form = HumanResourceSearchForm()
        self.assertIn('q', form.fields)
        self.assertIn('manager', form.fields)
        self.assertIn('job_title', form.fields)

        # Проверяем, что choices для должностей заполняются
        self.assertGreater(len(form.fields['job_title'].choices), 1)

    def test_human_resource_search_form_with_data(self):
        """Тест формы поиска с данными"""
        from hr.forms import HumanResourceSearchForm

        form_data = {
            'q': 'Тест',
            'manager': self.manager.pk,
            'job_title': 'Тестовый сотрудник',
            'only_managers': True,
            'is_active': 'true',
        }

        form = HumanResourceSearchForm(data=form_data)
        self.assertTrue(form.is_valid())
