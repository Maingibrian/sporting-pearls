"""Permission isolation tests — the Phase 1 release gate.

Matrix under test (who can reach the restricted store):

  anonymous      → login redirect
  parent         → bounced to their portal / 403
  staff          → neutral 403, and ZERO traces on the dashboard
  superuser      → neutral 403 too (role is an explicit, auditable grant)
  DSO            → full access
  ex-DSO         → access revoked with the group
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from parents.models import Guardian
from submissions.models import (FormSubmission, SafeguardingAuditEntry,
                                SafeguardingReport)
from submissions.safeguarding import (DSO_GROUP, STAFF_GROUP,
                                      migrate_legacy_rows)
from .test_safeguarding_parse import form10_payload

User = get_user_model()


def make_report(**over):
    """Test factory that mirrors the live API path: the report AND the
    audit entries the API writes (received + notified)."""
    from submissions.safeguarding import report_fields_for_create
    data = report_fields_for_create(form10_payload(**over))
    cats = data.pop('categories', '')
    report = SafeguardingReport.objects.create(
        ref=over.get('ref', 'SP-SAFE-20260101-T001'),
        ip='196.201.9.9', user_agent='test',
        categories=cats, **data)
    SafeguardingAuditEntry.objects.create(
        report=report, report_ref=report.ref, actor=None,
        actor_username='public form', action='received',
        detail='Report received through the website form.')
    SafeguardingAuditEntry.objects.create(
        report=report, report_ref=report.ref, actor=None,
        actor_username='public form', action='notified',
        detail='DSO notification: sent')
    return report


class AccessMatrixTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('staff1', 'staff1@example.com', 'pw-12345678',
                                             is_staff=True)
        cls.dso = User.objects.create_user('dso1', 'dso1@example.com', 'pw-12345678',
                                           is_staff=True)
        cls.dso.groups.add(Group.objects.get(name=DSO_GROUP))
        cls.superuser = User.objects.create_superuser('root', 'root@example.com', 'pw-12345678')
        cls.parent = User.objects.create_user('parent1', 'parent1@example.com', 'pw-12345678')
        Guardian.objects.create(user=cls.parent, full_name='Parent One')
        make_report()

    # -- the desk ----------------------------------------------------------

    def test_anonymous_redirected_to_login(self):
        r = self.client.get('/portal/dso/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/portal/login/', r['Location'])

    def test_parent_cannot_reach_desk(self):
        self.client.force_login(self.parent)
        r = self.client.get('/portal/dso/')
        self.assertIn(r.status_code, (302, 403))

    def test_staff_gets_neutral_403(self):
        self.client.force_login(self.staff)
        r = self.client.get('/portal/dso/')
        self.assertEqual(r.status_code, 403)
        # the page confirms nothing about what is behind the door
        self.assertNotIn('Safeguarding'.lower(), r.content.decode().lower())

    def test_superuser_without_role_is_locked_out(self):
        self.client.force_login(self.superuser)
        for url in ('/portal/dso/', '/portal/dso/audit/',
                    '/portal/dso/r/SP-SAFE-20260101-T001/'):
            self.assertEqual(self.client.get(url).status_code, 403, url)

    def test_dso_gets_full_access(self):
        self.client.force_login(self.dso)
        self.assertEqual(self.client.get('/portal/dso/').status_code, 200)
        self.assertEqual(self.client.get('/portal/dso/audit/').status_code, 200)
        r = self.client.get('/portal/dso/r/SP-SAFE-20260101-T001/')
        self.assertEqual(r.status_code, 200)

    def test_revoking_role_revokes_access(self):
        self.dso.groups.remove(Group.objects.get(name=DSO_GROUP))
        self.client.force_login(self.dso)
        self.assertEqual(self.client.get('/portal/dso/').status_code, 403)

    def test_staff_cannot_post_status_or_notes(self):
        self.client.force_login(self.staff)
        r = self.client.post('/portal/dso/r/SP-SAFE-20260101-T001/',
                             {'action': 'status', 'status': 'closed'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(SafeguardingReport.objects.first().status, 'received')

    # -- the staff dashboard must not leak existence ------------------------

    def test_dashboard_blind_to_safeguarding(self):
        make_report(ref='SP-SAFE-20260101-T002')  # a second report
        self.client.force_login(self.staff)
        r = self.client.get('/portal/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertNotIn('SP-SAFE', html)                       # no reference
        self.assertNotIn('Safeguarding desk', html)             # no nav item
        self.assertNotIn('Test Child', html)                     # no content
        self.assertNotIn('form-10-safeguarding-report', html)    # no slug

    def test_dashboard_shows_dso_nav_for_dso_only(self):
        self.client.force_login(self.dso)
        html = self.client.get('/portal/').content.decode()
        self.assertIn('Safeguarding desk', html)
        self.client.force_login(self.staff)
        html = self.client.get('/portal/').content.decode()
        self.assertNotIn('Safeguarding desk', html)

    # -- Django admin gating --------------------------------------------------

    def test_admin_hides_store_from_staff_and_bare_superuser(self):
        for user in (self.staff, self.superuser):
            self.client.force_login(user)
            r = self.client.get('/admin/submissions/safeguardingreport/')
            self.assertEqual(r.status_code, 403, user.username)

    def test_admin_allows_dso_readonly(self):
        self.client.force_login(self.dso)
        r = self.client.get('/admin/submissions/safeguardingreport/')
        self.assertEqual(r.status_code, 200)
        # read-only: no add / delete surfaces
        html = r.content.decode()
        self.assertNotIn(' class="addlink"', html)


class AuditImmutabilityTests(TestCase):

    def test_entries_cannot_be_updated_or_deleted(self):
        report = make_report()
        entry = SafeguardingAuditEntry.objects.create(
            report=report, report_ref=report.ref, actor=None,
            actor_username='test', action='received', detail='x')
        with self.assertRaises(RuntimeError):
            entry.detail = 'rewritten'
            entry.save()
        with self.assertRaises(RuntimeError):
            entry.delete()


class GroupsExistTests(TestCase):

    def test_groups_created_by_migration(self):
        names = set(Group.objects.values_list('name', flat=True))
        self.assertIn(DSO_GROUP, names)
        self.assertIn(STAFF_GROUP, names)
        dso = Group.objects.get(name=DSO_GROUP)
        codenames = {p.codename for p in dso.permissions.all()}
        self.assertIn('view_safeguardingreport', codenames)
        self.assertIn('view_safeguardingreport_restricted', codenames)
        self.assertIn('view_safeguardingauditentry', codenames)
        # the DSO group grants nothing else — least privilege
        self.assertEqual(len(codenames), 3)

    def test_portal_admin_group_has_account_perms_only(self):
        from submissions.safeguarding import PORTAL_ADMIN_GROUP
        admins = Group.objects.get(name=PORTAL_ADMIN_GROUP)
        codenames = {p.codename for p in admins.permissions.all()}
        self.assertTrue({'view_user', 'add_user', 'change_user',
                         'view_group'} <= codenames)
        # and critically: NO safeguarding access for administrators
        self.assertEqual(codenames & {'view_safeguardingreport',
                                      'view_safeguardingreport_restricted',
                                      'view_safeguardingauditentry'}, set())
