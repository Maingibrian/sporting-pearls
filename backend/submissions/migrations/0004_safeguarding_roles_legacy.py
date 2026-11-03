"""Phase 1 — roles and the legacy safeguarding ledger move.

Two jobs, both idempotent:

1. Create the three Django groups (Academy Staff, DSO, Portal
   Administrators) and wire the DSO group to the restricted safeguarding
   permissions. Parent/Guardian is a profile (parents.Guardian), not a
   group — documented in SAFEGUARDING-RUNBOOK.md.

2. Move every legacy form-10 FormSubmission row into the restricted
   SafeguardingReport store (via safeguarding.migrate_legacy_rows) so
   upgrading installs stop exposing those reports to the staff ledger,
   dashboard and CSV export immediately.

No staff account gains safeguarding access from this migration: the DSO
group starts empty; the owner grants it explicitly with
`python manage.py sp_dso grant <username>` (see the runbook).
"""
from django.db import migrations

from submissions.safeguarding import (
    DSO_GROUP, PORTAL_ADMIN_GROUP, STAFF_GROUP, migrate_legacy_rows,
)


def create_groups_and_move_legacy(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')

    # 1) groups
    Group.objects.update_or_create(name=STAFF_GROUP, defaults={})
    Group.objects.update_or_create(name=PORTAL_ADMIN_GROUP, defaults={})
    dso, _ = Group.objects.update_or_create(name=DSO_GROUP, defaults={})

    # 2) DSO permissions (restricted store only). Default permissions are
    # created by the post_migrate signal — which runs only AFTER the whole
    # migrate command — so on a fresh (or upgrading) install they do not
    # exist yet while this migration runs. Create them explicitly and
    # idempotently; post_migrate will reconcile names later.
    ContentType = apps.get_model('contenttypes', 'ContentType')
    wanted = [
        ('view_safeguardingreport', 'safeguardingreport',
         'Can view safeguarding report'),
        ('view_safeguardingreport_restricted', 'safeguardingreport',
         'Can view safeguarding reports (DSO store)'),
        ('view_safeguardingauditentry', 'safeguardingauditentry',
         'Can view safeguarding audit entry'),
    ]
    for codename, model_name, name in wanted:
        ct, _ = ContentType.objects.update_or_create(
            app_label='submissions', model=model_name,
            defaults={'app_label': 'submissions', 'model': model_name})
        perm, _ = Permission.objects.update_or_create(
            codename=codename, content_type=ct, defaults={'name': name})
        dso.permissions.add(perm)

    # 2b) Portal Administrators manage accounts — never the safeguarding
    # store (no safeguarding permissions granted here, by design).
    admins, _ = Group.objects.update_or_create(name=PORTAL_ADMIN_GROUP, defaults={})
    admin_wanted = [
        # (app_label, model, codename, name)
        ('auth', 'user', 'view_user', 'Can view user'),
        ('auth', 'user', 'add_user', 'Can add user'),
        ('auth', 'user', 'change_user', 'Can change user'),
        ('auth', 'group', 'view_group', 'Can view group'),
        ('auth', 'group', 'add_group', 'Can add group'),
        ('auth', 'group', 'change_group', 'Can change group'),
        ('admin', 'logentry', 'view_logentry', 'Can view log entry'),
    ]
    for app_label, model, codename, name in admin_wanted:
        ct, _ = ContentType.objects.update_or_create(
            app_label=app_label, model=model,
            defaults={'app_label': app_label, 'model': model})
        perm, _ = Permission.objects.update_or_create(
            codename=codename, content_type=ct, defaults={'name': name})
        admins.permissions.add(perm)

    # 3) legacy rows -> restricted store
    migrate_legacy_rows(apps)


def revert(apps, schema_editor):
    """Downgrade removes the groups; reports stay in the restricted store
    (moving them back to the open ledger would be a data-protection
    regression, so the store is preserved — dropping the models is left
    to the schema migration itself)."""
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[DSO_GROUP, STAFF_GROUP, PORTAL_ADMIN_GROUP]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0003_safeguarding'),
    ]

    operations = [
        migrations.RunPython(create_groups_and_move_legacy, revert),
    ]
