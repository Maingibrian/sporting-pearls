#!/usr/bin/env python3
"""Sporting Pearls — Django backend (forms API + fixtures + admin dashboard)."""
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sporting_pearls_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Activate the project's virtualenv "
            "(.venv) or install the requirements: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
