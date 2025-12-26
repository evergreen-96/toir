#!/usr/bin/env python
import os
import sys
import subprocess


def run_tests():
    """Запускает все тесты приложения assets"""
    print("Запуск тестов приложения assets...")
    print("=" * 60)

    # Настройка переменных окружения
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'toir_project.settings')

    # Запуск тестов (убираем test_api, если нет DRF)
    test_cases = [
        'assets.tests.test_models',
        'assets.tests.test_forms',
        'assets.tests.test_views',
        'assets.tests.test_signals',
        'assets.tests.test_integration',
        # 'assets.tests.test_api',  # Пропускаем, если нет DRF
    ]

    for test_case in test_cases:
        print(f"\nЗапуск {test_case}...")
        result = subprocess.run([
            'python', 'manage.py', 'test', test_case,
            '--verbosity=2',
            '--no-input'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ {test_case} - УСПЕХ")
        else:
            print(f"❌ {test_case} - ОШИБКА")
            print(result.stdout)
            print(result.stderr)

    print("\n" + "=" * 60)
    print("Запуск всех тестов завершен")


if __name__ == '__main__':
    run_tests()
# [file content end]