"""Creates the admin superuser from environment variables on first run.
Safe to run on every deploy: it does nothing once a superuser exists.

Required env:  DJANGO_SUPERUSER_PASSWORD
Optional env:  DJANGO_SUPERUSER_USERNAME (default: admin)
               DJANGO_SUPERUSER_EMAIL    (default: info@sp)
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the admin superuser from env vars (no-op once one exists).'

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('superuser already exists — skipping')
            return
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'info@sp')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        if not password:
            self.stderr.write('DJANGO_SUPERUSER_PASSWORD not set — cannot create superuser')
            raise SystemExit(1)
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'superuser "{username}" created'))
