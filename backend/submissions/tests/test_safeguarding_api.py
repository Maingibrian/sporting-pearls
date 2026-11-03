"""Public API tests for the safeguarding stream (form 10).

Verifies the three promises of Phase 1 at the API layer:
1. Reports land ONLY in the restricted store — the staff ledger stays
   empty (no row, no count, nothing to infer from).
2. The DSO notification email is minimal (reference + link only).
3. Reporter acknowledgment is neutral, and anonymous reports get none.
"""
import json
from unittest import mock

from django.test import TestCase, override_settings

from submissions.models import FormSubmission, SafeguardingAuditEntry, SafeguardingReport
from .test_safeguarding_parse import form10_payload

API = '/api/forms/form-10-safeguarding-report/'


class SafeguardingAPITests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.sent = []

    def _fake_resend(self, kind='ok'):
        def send(payload):
            self.sent.append(payload)
            if kind == 'ok':
                return True, 'sent'
            return False, 'HTTP 500: test'
        return send

    def _post(self, payload, ip='196.201.9.9'):
        return self.client.post(
            API, data=json.dumps({'slug': 'form-10-safeguarding-report',
                                  'data': payload, 'meta': {'ua': 'test-agent'}}),
            content_type='application/json', REMOTE_ADDR=ip)

    def test_report_stored_in_restricted_store_not_ledger(self):
        with mock.patch('submissions.views.resend_send', self._fake_resend()):
            with override_settings(DSO_EMAIL='dso@example.com'):
                r = self._post(form10_payload())
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body['ok'])
        self.assertTrue(body['ref'].startswith('SP-SAFE-'))

        self.assertEqual(SafeguardingReport.objects.count(), 1)
        report = SafeguardingReport.objects.get(ref=body['ref'])
        self.assertEqual(report.child_name, 'Test Child')
        self.assertEqual(report.reporter_preference, 'confidential')
        self.assertIn('Physical harm', report.categories)

        # the ledger — the surface every staff account can query — stays blind
        self.assertEqual(FormSubmission.objects.count(), 0)
        self.assertFalse(FormSubmission.objects.filter(
            form_slug='form-10-safeguarding-report').exists())

        # audit: received + notified
        actions = [e.action for e in report.audit_entries.all()]
        self.assertIn('received', actions)
        self.assertIn('notified', actions)

    def test_dso_notification_is_minimal(self):
        """No narrative, child name, reporter identity or contact details
        may appear in the notification email (subject, text or html)."""
        with mock.patch('submissions.views.resend_send', self._fake_resend()):
            with override_settings(DSO_EMAIL='dso@example.com'):
                self._post(form10_payload())

        self.assertEqual(len(self.sent), 2)  # DSO notification + reporter ack
        note = self.sent[0]
        self.assertEqual(note['to'], ['dso@example.com'])
        blob = note['subject'] + note['text'] + note['html']
        for secret in ('Test Child', 'Factual narrative here', 'Jane Mwangi',
                       'jane@example.com', '0711 000 000', 'A. Coach',
                       'Main pitch'):
            self.assertNotIn(secret, blob, f'LEAK in DSO notification: {secret}')
        self.assertIn('/portal/dso/', blob)

    def test_reporter_ack_is_neutral_and_only_for_confidential(self):
        with mock.patch('submissions.views.resend_send', self._fake_resend()):
            with override_settings(DSO_EMAIL='dso@example.com'):
                self._post(form10_payload())
        ack = self.sent[1]
        self.assertEqual(ack['to'], ['jane@example.com'])
        # subject stays neutral (shared inboxes); body carries no case content
        self.assertNotIn('Safeguarding', ack['subject'])
        for secret in ('Test Child', 'Factual narrative here', 'A. Coach'):
            self.assertNotIn(secret, ack['subject'] + ack['text'] + ack['html'])

        # anonymous report → no ack at all
        self.sent.clear()
        with mock.patch('submissions.views.resend_send', self._fake_resend()):
            with override_settings(DSO_EMAIL='dso@example.com'):
                self._post(form10_payload(**{
                    'Reporting Preference': 'Completely Anonymous',
                    'Reporter Full Name': 'X', 'Email Address': 'x@example.com'}))
        self.assertEqual(len(self.sent), 1)  # DSO notification only

    def test_no_dso_email_means_no_academy_email(self):
        """Unset DSO_EMAIL must fail safe: nothing to any academy inbox —
        only the reporter's own acknowledgment may still go out."""
        with mock.patch('submissions.views.resend_send', self._fake_resend()):
            with override_settings(DSO_EMAIL=''):
                r = self._post(form10_payload())
        self.assertEqual(r.status_code, 200)
        # the only email out is the reporter's own neutral acknowledgment
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]['to'], ['jane@example.com'])
        report = SafeguardingReport.objects.get(ref=r.json()['ref'])
        self.assertIn('skipped', report.email_status)

    def test_notification_failure_is_recorded_not_raised(self):
        with mock.patch('submissions.views.resend_send', self._fake_resend('fail')):
            with override_settings(DSO_EMAIL='dso@example.com'):
                r = self._post(form10_payload())
        self.assertEqual(r.status_code, 200)  # report is stored regardless
        report = SafeguardingReport.objects.first()
        self.assertIn('HTTP 500', report.email_error)

    def test_honeypot_still_drops(self):
        r = self._post({**form10_payload(), 'company': 'spam-bot'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SafeguardingReport.objects.count(), 0)

    def test_other_forms_still_use_ledger(self):
        r = self.client.post(
            '/api/forms/form-08-contact-form/',
            data=json.dumps({'slug': 'form-08-contact-form',
                             'data': {'Name': 'Ordinary Person',
                                      'Email Address': 'p@example.com',
                                      'Message': 'hello'},
                             'meta': {}}),
            content_type='application/json', REMOTE_ADDR='196.201.9.10')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(FormSubmission.objects.count(), 1)
        self.assertEqual(SafeguardingReport.objects.count(), 0)

    def test_legacy_rows_are_migrated_and_audited(self):
        from submissions.safeguarding import migrate_legacy_rows
        legacy = FormSubmission.objects.create(
            ref='SP-SAFE-20260101-LEG1', form_slug='form-10-safeguarding-report',
            name='Old Reporter', email='old@example.com',
            payload=form10_payload())
        moved = migrate_legacy_rows()
        self.assertEqual(moved, 1)
        self.assertFalse(FormSubmission.objects.filter(id=legacy.id).exists())
        report = SafeguardingReport.objects.get(ref='SP-SAFE-20260101-LEG1')
        self.assertEqual(report.child_name, 'Test Child')
        self.assertEqual(
            [e.action for e in report.audit_entries.all()], ['migrated'])
        # idempotent
        self.assertEqual(migrate_legacy_rows(), 0)
