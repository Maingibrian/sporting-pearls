"""DSO desk workflow tests — the operational path of a report.

Covers: view auditing, status transitions, assignment, case notes, and
the full audit trail a review would inspect.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from submissions.models import SafeguardingAuditEntry, SafeguardingReport
from submissions.safeguarding import DSO_GROUP
from .test_safeguarding_access import make_report

User = get_user_model()
REF = 'SP-SAFE-20260101-W001'


class DeskWorkflowTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.dso = User.objects.create_user('dso2', 'dso2@example.com', 'pw-12345678',
                                           is_staff=True)
        cls.dso.groups.add(Group.objects.get(name=DSO_GROUP))
        cls.report = make_report(ref=REF)

    def setUp(self):
        self.client.force_login(self.dso)

    def test_viewing_report_writes_audit_entry(self):
        self.client.get(f'/portal/dso/r/{REF}/')
        self.assertTrue(SafeguardingAuditEntry.objects.filter(
            report=self.report, action='viewed',
            actor_username='dso2').exists())

    def test_status_change_audited_with_old_and_new(self):
        r = self.client.post(f'/portal/dso/r/{REF}/',
                             {'action': 'status', 'status': 'under_review'})
        self.assertEqual(r.status_code, 302)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'under_review')
        entry = SafeguardingAuditEntry.objects.filter(
            report=self.report, action='status_changed').latest('created_at')
        self.assertEqual(entry.actor_username, 'dso2')
        self.assertIn('Received', entry.detail)
        self.assertIn('Under review', entry.detail)
        # first status change auto-assigns the acting DSO
        self.assertEqual(self.report.assigned_to, self.dso)

    def test_invalid_status_rejected(self):
        self.client.post(f'/portal/dso/r/{REF}/',
                         {'action': 'status', 'status': 'hacked'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'received')

    def test_case_note_is_recorded_verbatim(self):
        self.client.post(f'/portal/dso/r/{REF}/',
                         {'action': 'note', 'note': 'Called the Children Officer at 10:00.'})
        entry = SafeguardingAuditEntry.objects.filter(
            report=self.report, action='note_added').first()
        self.assertIsNotNone(entry)
        self.assertIn('Children Officer', entry.detail)

    def test_empty_note_rejected(self):
        self.client.post(f'/portal/dso/r/{REF}/', {'action': 'note', 'note': '  '})
        self.assertFalse(SafeguardingAuditEntry.objects.filter(
            report=self.report, action='note_added').exists())

    def test_assign_to_me_audited(self):
        self.client.post(f'/portal/dso/r/{REF}/', {'action': 'assign'})
        self.report.refresh_from_db()
        self.assertEqual(self.report.assigned_to, self.dso)
        self.assertTrue(SafeguardingAuditEntry.objects.filter(
            report=self.report, action='assigned').exists())

    def test_full_lifecycle_leaves_complete_trail(self):
        """received → under_review → escalated → closed with notes along the way.
        follow=True mimics the browser: every action lands back on the
        detail page, which itself writes a 'viewed' entry."""
        for status in ('under_review', 'escalated_external', 'closed'):
            self.client.post(f'/portal/dso/r/{REF}/',
                             {'action': 'status', 'status': status}, follow=True)
            self.client.post(f'/portal/dso/r/{REF}/',
                             {'action': 'note', 'note': f'note after {status}'},
                             follow=True)
        actions = list(self.report.audit_entries
                       .values_list('action', flat=True))
        self.assertEqual(actions.count('status_changed'), 3)
        self.assertEqual(actions.count('note_added'), 3)
        self.assertEqual(actions.count('viewed'), 6)
        self.assertIn('received', actions)     # from creation
        self.assertIn('notified', actions)

    def test_queue_lists_report_but_not_narrative(self):
        html = self.client.get('/portal/dso/').content.decode()
        self.assertIn(REF, html)
        self.assertIn('Test Child', html)
        # the queue is DSO-only, but it still should not carry the narrative
        self.assertNotIn('Factual narrative here', html)

    def test_audit_page_lists_entries(self):
        self.client.get(f'/portal/dso/r/{REF}/')
        html = self.client.get('/portal/dso/audit/').content.decode()
        self.assertIn(REF, html)
        self.assertIn('received', html)

    def test_unknown_ref_redirects_to_queue(self):
        r = self.client.get('/portal/dso/r/SP-SAFE-00000000-XXXX/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], '/portal/dso/')
