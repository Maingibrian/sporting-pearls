"""Phase 4 tests — admin-settable coaching staff.

Covers the Coach model's public surface exactly as the website consumes
it: the /api/coaches/ endpoint (published coaches only, correct shape
and ordering), the media gate's new coaches/ branch (published photos
public, everything else 404 to anonymous visitors), and the hardened
admin photo upload (renamed non-images rejected, EXIF stripped on the
stored copy, extension matching the real format).
"""
import io
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from PIL import Image

from submissions.models import Coach, Squad

User = get_user_model()


def _jpeg_bytes_with_exif():
    """A real JPEG carrying EXIF metadata (orientation tag)."""
    buf = io.BytesIO()
    img = Image.new('RGB', (60, 40), (200, 60, 20))
    exif = Image.Exif()
    exif[0x0112] = 6                      # orientation: rotated
    exif[0x0131] = 'QA test software'     # Software tag
    img.save(buf, 'JPEG', exif=exif)
    return buf.getvalue()


def _png_bytes():
    buf = io.BytesIO()
    Image.new('RGB', (50, 50), (20, 90, 160)).save(buf, 'PNG')
    return buf.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='sp-p4-media-'))
class CoachesEndpointTests(TestCase):
    def setUp(self):
        self.squad = Squad.objects.create(key='u15', code='U15',
                                          label='U15 Performance Squad')
        Coach.objects.create(name='Hidden Coach', role='Assistant Coach',
                             squad=self.squad, sort=2)
        Coach.objects.create(name='Amina Trainer', role='Head Coach',
                             squad=self.squad, sort=1, is_published=True,
                             bio='Leads the academy technical programme.')
        Coach.objects.create(name='Bilali Keeper', role='Goalkeeper Coach',
                             squad=None, sort=3, is_published=True)

    def test_only_published_coaches_are_listed_in_sort_order(self):
        r = self.client.get('/api/coaches/')
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue(j['ok'])
        self.assertEqual(j['count'], 2)
        names = [c['name'] for c in j['coaches']]
        self.assertEqual(names, ['Amina Trainer', 'Bilali Keeper'])
        self.assertNotIn('Hidden Coach', names)

    def test_payload_shape(self):
        j = self.client.get('/api/coaches/').json()
        first = j['coaches'][0]
        self.assertEqual(set(first.keys()),
                         {'name', 'role', 'squad', 'bio', 'photo'})
        self.assertEqual(first['squad'], 'U15 Performance Squad')
        self.assertEqual(first['bio'], 'Leads the academy technical programme.')
        self.assertEqual(first['photo'], '')   # no photo uploaded

    def test_coach_without_squad_has_empty_label(self):
        j = self.client.get('/api/coaches/').json()
        second = j['coaches'][1]
        self.assertEqual(second['squad'], '')

    def test_photo_url_is_absolute_and_points_at_media_gate(self):
        c = Coach.objects.filter(is_published=True).first()
        c.photo.save('coach-qa.jpg',
                     __import__('django.core.files.base', fromlist=['ContentFile'])
                     .ContentFile(_jpeg_bytes_with_exif()), save=True)
        j = self.client.get('/api/coaches/').json()
        photo = next(x['photo'] for x in j['coaches'] if x['name'] == c.name)
        self.assertIn('/media/coaches/', photo)
        self.assertTrue(photo.startswith('http'))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(Path(__import__('django.conf', fromlist=['settings'])
                           .settings.MEDIA_ROOT), ignore_errors=True)
        super().tearDownClass()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='sp-p4-gate-'))
class CoachMediaGateTests(TestCase):
    def setUp(self):
        from django.core.files.base import ContentFile
        self.squad = Squad.objects.create(key='u17', code='U17',
                                          label='U17 Transition Squad')
        self.published = Coach.objects.create(
            name='Published Coach', role='Fitness Coach', is_published=True)
        self.published.photo.save('coach-pub.jpg',
                                  ContentFile(_jpeg_bytes_with_exif()), save=True)
        self.unpublished = Coach.objects.create(
            name='Draft Coach', role='Assistant Coach', is_published=False)
        self.unpublished.photo.save('coach-draft.jpg',
                                    ContentFile(_jpeg_bytes_with_exif()), save=True)
        self.staff = User.objects.create_user('p4staff', password='x' * 12,
                                              is_staff=True)

    def test_published_coach_photo_is_public(self):
        r = Client().get(f'/media/{self.published.photo.name}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('image/', r['Content-Type'])

    def test_unpublished_coach_photo_is_404_anonymous_200_staff(self):
        anon = Client().get(f'/media/{self.unpublished.photo.name}')
        self.assertEqual(anon.status_code, 404)
        staff = Client()
        staff.force_login(self.staff)
        r = staff.get(f'/media/{self.unpublished.photo.name}')
        self.assertEqual(r.status_code, 200)

    def test_stored_coach_photo_has_no_exif(self):
        saved = Image.open(Path(
            __import__('django.conf', fromlist=['settings']).settings.MEDIA_ROOT,
            self.published.photo.name))
        saved.load()
        self.assertEqual(dict(saved.getexif()), {})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(Path(__import__('django.conf', fromlist=['settings'])
                           .settings.MEDIA_ROOT), ignore_errors=True)
        super().tearDownClass()


class CoachAdminPhotoValidationTests(TestCase):
    """The admin form runs the same pipeline as the portal player-photo
    upload (Phase 2, T37–T39) — these exercise CoachAdminForm directly."""

    def _form(self, uploaded):
        from submissions.admin import CoachAdminForm
        data = {'name': 'QA Coach', 'role': 'Head Coach', 'sort': 0}
        files = {'photo': uploaded} if uploaded is not None else {}
        return CoachAdminForm(data=data, files=files)

    def test_renamed_text_file_is_rejected(self):
        up = SimpleUploadedFile('not-a-photo.jpg', b'this is plain text, not an image',
                                content_type='image/jpeg')
        form = self._form(up)
        self.assertFalse(form.is_valid())
        self.assertIn('photo', form.errors)

    def test_disallowed_extension_is_rejected(self):
        up = SimpleUploadedFile('photo.gif', _png_bytes(), content_type='image/png')
        form = self._form(up)
        self.assertFalse(form.is_valid())
        self.assertIn('photo', form.errors)

    def test_valid_jpeg_passes_validation_unchanged(self):
        up = SimpleUploadedFile('coach photo.jpeg', _jpeg_bytes_with_exif(),
                                content_type='image/jpeg')
        form = self._form(up)
        self.assertTrue(form.is_valid(), getattr(form, 'errors', None))

    def test_png_passes_validation(self):
        up = SimpleUploadedFile('portrait.png', _png_bytes(), content_type='image/png')
        form = self._form(up)
        self.assertTrue(form.is_valid(), getattr(form, 'errors', None))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='sp-p4-store-'))
class CoachPhotoStorageTests(TestCase):
    """The storage enforces the re-encode on EVERY save path — including
    direct model writes that bypass the admin form (that's the point of
    putting the pipeline in CoachPhotoStorage rather than the form)."""

    def test_direct_save_strips_exif_and_fixes_extension(self):
        c = Coach(name='Storage QA', role='Head Coach', is_published=True)
        c.photo.save('coach photo.jpeg',
                     __import__('django.core.files.base', fromlist=['ContentFile'])
                     .ContentFile(_jpeg_bytes_with_exif()), save=True)
        self.assertTrue(c.photo.name.startswith('coaches/coach-'))
        self.assertTrue(c.photo.name.endswith('.jpg'))
        self.assertNotIn(' ', c.photo.name)
        saved = Image.open(Path(
            __import__('django.conf', fromlist=['settings']).settings.MEDIA_ROOT,
            c.photo.name))
        saved.load()
        self.assertEqual(dict(saved.getexif()), {})
        self.assertEqual(saved.format, 'JPEG')

    def test_direct_save_of_unreadable_file_fails_closed(self):
        c = Coach(name='Bad File QA', role='Assistant Coach')
        with self.assertRaises(ValueError):
            c.photo.save('evil.jpg',
                         __import__('django.core.files.base', fromlist=['ContentFile'])
                         .ContentFile(b'definitely not an image'), save=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(Path(__import__('django.conf', fromlist=['settings'])
                           .settings.MEDIA_ROOT), ignore_errors=True)
        super().tearDownClass()
