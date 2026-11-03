"""Grant, revoke or list the DSO (Designated Safeguarding Officer) role.

The DSO role is the ONLY key to the restricted safeguarding store
(/portal/dso/, the safeguarding models in the admin). It is granted
explicitly, per person, and never inherited — not even by superusers.

Usage:
    python manage.py sp_dso list
    python manage.py sp_dso grant <username>
    python manage.py sp_dso revoke <username>

Granting the role also flips is_staff on (needed to reach the portal at
all). Revoking removes the group but leaves is_staff untouched — check
whether the account still needs staff access at all.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from submissions.safeguarding import DSO_GROUP

try:
    from django.contrib.auth.models import Group
except ImportError:  # pragma: no cover
    Group = None


class Command(BaseCommand):
    help = 'Manage the DSO (safeguarding) role: list / grant / revoke.'

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['list', 'grant', 'revoke'])
        parser.add_argument('username', nargs='?', default='')

    def handle(self, *args, **opts):
        action, username = opts['action'], opts['username'].strip()
        group, _ = Group.objects.get_or_create(name=DSO_GROUP)

        if action == 'list':
            members = group.user_set.all().order_by('username')
            if not members:
                self.stdout.write(self.style.WARNING(
                    'No DSO appointed. Safeguarding reports will pile up unseen '
                    'in /portal/dso/ — appoint the Safeguarding Lead with:\n'
                    '  python manage.py sp_dso grant <username>'))
                return
            self.stdout.write(f'DSO role ({DSO_GROUP}) — {members.count()} member(s):')
            for u in members:
                self.stdout.write(f'  - {u.username}'
                                  + ('  (superuser)' if u.is_superuser else ''))
            return

        if not username:
            raise CommandError(f'Usage: python manage.py sp_dso {action} <username>')

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is None:
            raise CommandError(f'No user named "{username}".')

        if action == 'grant':
            if not user.is_active:
                raise CommandError(f'"{username}" is inactive — activate the account first.')
            group.user_set.add(user)
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'])
                self.stdout.write('is_staff switched ON (needed to reach the portal).')
            self.stdout.write(self.style.SUCCESS(
                f'"{username}" now holds the DSO role and can open /portal/dso/.'))
            self.stdout.write(self.style.NOTICE(
                'Keep this list short (ideally one officer + one deputy). '
                'Every view and action there is written to the audit log.'))
        else:  # revoke
            group.user_set.remove(user)
            self.stdout.write(self.style.SUCCESS(
                f'"{username}" no longer holds the DSO role.'))
            self.stdout.write(self.style.NOTICE(
                'Their is_staff flag was left as it was — disable the account or '
                'remove staff access separately if they no longer need it.'))
