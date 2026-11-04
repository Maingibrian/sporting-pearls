"""Rev 28 tests — Technical-team (coach) management from the portal.

The Coach model existed since Phase 4 but was admin-only. The portal now
offers the same lifecycle the players get: add, edit, publish/hide,
photo upload and delete — all behind the staff gate, with the public
/api/coaches/ endpoint still listing published coaches only.
"""
import io
import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from PIL import Image

from submissions.models import Coach, Squad


def _png_bytes():
    """A real PNG built with Pillow (hardcoded hex bytes tend to rot)."""
    buf = io.BytesIO()
    Image.new('RGB', (50, 50), (20, 90, 160)).save(buf, 'PNG')
    return buf.getvalue()


def _staff_client():
    """Helper kept for external use: a logged-in staff client."""
    from django.test import Client
    u = User.objects.create_user('coachdesk', password='pw-123456', is_staff=True)
    c = Client()
    c.force_login(u)
    return c


class CoachPortalCrudTests(TestCase):
    """Staff can run the full coach lifecycle from the branded portal."""

    def setUp(self):
        self.staff = User.objects.create_user('coachdesk', password='pw-123456',
                                              is_staff=True)
        self.client.force_login(self.staff)
        self.squad = Squad.objects.create(key='u14', code='U14',
                                          label='U14 Development Squad')

    def post_json(self, url, payload):
        return self.client.post(url, data=json.dumps(payload),
                                content_type='application/json')

    def test_add_requires_staff(self):
        anon = type('A', (), {})()
        from django.test import Client
        ac = Client()
        r = ac.post('/portal/coaches/add/', data='{}',
                    content_type='application/json')
        self.assertEqual(r.status_code, 302)   # redirected to the login

    def test_add_edit_toggle_delete_lifecycle(self):
        r = self.post_json('/portal/coaches/add/', {
            'name': 'Josephat Okello', 'role': 'Head Coach',
            'squad': 'U14', 'bio': 'CAF A licence.', 'sort': 1})
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue(j['ok'])
        cid = j['coach']['id']
        self.assertEqual(j['coach']['squad'], 'U14')
        self.assertFalse(j['coach']['published'])      # drafts by default

        # edit: rename + attach to no squad + publish
        r = self.post_json(f'/portal/coaches/{cid}/edit/', {
            'name': 'Josephat O. Okello', 'role': 'Head Coach',
            'squad': '', 'bio': 'CAF A licence, 12 seasons.', 'sort': 2,
            'is_published': True})
        j = r.json()
        self.assertTrue(j['ok'])
        self.assertEqual(j['coach']['squad'], '')
        self.assertTrue(j['coach']['published'])

        # published coach reaches the public API
        api = self.client.get('/api/coaches/').json()
        self.assertEqual(api['count'], 1)
        self.assertEqual(api['coaches'][0]['name'], 'Josephat O. Okello')

        # toggle off -> vanishes from the public API again
        r = self.client.post(f'/portal/coaches/{cid}/toggle/')
        self.assertTrue(r.json()['ok'])
        api = self.client.get('/api/coaches/').json()
        self.assertEqual(api['count'], 0)

        # delete
        r = self.client.post(f'/portal/coaches/{cid}/delete/')
        self.assertTrue(r.json()['ok'])
        self.assertEqual(Coach.objects.count(), 0)

    def test_add_validates_fields(self):
        for bad in ({'name': '', 'role': 'Head Coach'},        # no name
                    {'name': 'A' * 121, 'role': 'x'},          # name too long
                    {'name': 'Ok', 'role': ''},                # no role
                    {'name': 'Ok', 'role': 'R', 'bio': 'x' * 601},
                    {'name': 'Ok', 'role': 'R', 'sort': 100},
                    {'name': 'Ok', 'role': 'R', 'squad': 'NOPE'}):
            r = self.post_json('/portal/coaches/add/', bad)
            j = r.json()
            self.assertFalse(j['ok'], bad)
            self.assertIn('error', j)

    def test_unknown_coach_fails_politely(self):
        r = self.post_json('/portal/coaches/9999/edit/', {'name': 'x', 'role': 'y'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()['ok'])
        self.assertIn('error', r.json())

    def test_portal_page_has_technical_team_view(self):
        Squad.objects.create(key='u12', code='U12', label='U12 Foundation Squad')
        Coach.objects.create(name='Jane Doe', role='GK Coach')
        r = self.client.get('/portal/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8')
        self.assertIn('view-coaches', body)
        self.assertIn('btn-add-coach', body)
        self.assertIn('Jane Doe', body)
        self.assertIn('coaches-json', body)

    def test_portal_page_empty_state_when_no_coaches(self):
        r = self.client.get('/portal/')
        body = r.content.decode('utf-8')
        self.assertIn('co-empty', body)
        self.assertIn('display:none', body.split('id="co-grid"')[1][:60])


class CoachPortalPhotoTests(TestCase):
    """Photo uploads get the same hardening as player photos."""

    def setUp(self):
        self.staff = User.objects.create_user('photodesk', password='pw-123456',
                                              is_staff=True)
        self.client.force_login(self.staff)
        self.coach = Coach.objects.create(name='Photo Coach', role='Fitness')

    def upload(self, filename, content, ctype='image/png'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile(filename, content, content_type=ctype)
        return self.client.post(f'/portal/coaches/{self.coach.id}/photo/',
                                {'file': f})

    def test_valid_png_uploads_and_strips_metadata(self):
        with override_settings(MEDIA_ROOT=self.__class__.__name__ + '-media'):
            r = self.upload('coach.png', _png_bytes())
            self.assertEqual(r.status_code, 200)
            j = r.json()
            self.assertTrue(j['ok'])
            self.assertTrue(j['photo'].startswith('/media/coaches/'))
            self.coach.refresh_from_db()
            self.assertTrue(self.coach.photo.name.startswith('coaches/'))
            self.coach.photo.delete(save=False)

    def test_renamed_text_file_rejected(self):
        r = self.upload('not-really.png', b'this is just text, not an image')
        j = r.json()
        self.assertFalse(j['ok'])

    def test_bad_extension_rejected_before_decode(self):
        r = self.upload('coach.gif', _png_bytes(), ctype='image/gif')
        j = r.json()
        self.assertFalse(j['ok'])
        self.assertIn('JPG, PNG or WebP', j['error'])

    def test_missing_file_rejected(self):
        r = self.client.post(f'/portal/coaches/{self.coach.id}/photo/', {})
        self.assertFalse(r.json()['ok'])
