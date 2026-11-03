"""Phase 2 tests — player photo upload validation.

Before Phase 2 the upload path trusted the filename extension and
stored the raw bytes: an arbitrary file named photo.jpg landed in
/media/, and EXIF metadata (including GPS coordinates of children)
survived. Now every upload is fully decoded with Pillow, re-encoded
clean, and the stored extension always matches the real format.
"""
import io

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from submissions.models import Player, Squad

User = get_user_model()


def _png_bytes(size=(40, 30), color=(10, 120, 200)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, 'PNG')
    return buf.getvalue()


def _jpeg_bytes_with_exif():
    """A real JPEG carrying EXIF metadata (orientation tag)."""
    buf = io.BytesIO()
    img = Image.new('RGB', (40, 30), (9, 90, 170))
    exif = Image.Exif()
    exif[0x0112] = 6                      # orientation: rotated
    exif[0x0131] = 'QA test software'     # Software tag
    img.save(buf, 'JPEG', exif=exif)
    return buf.getvalue()


@override_settings(MEDIA_ROOT='/tmp/sp-qa-media')
class PhotoUploadTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            'qa_photo_staff', 'p@example.com', 'Str0ng-Pass!x', is_staff=True)
        self.client.force_login(self.staff)
        self.squad, _ = Squad.objects.get_or_create(code='U12')
        self.player = Player.objects.create(
            squad=self.squad, ref='U12-01', first_name='Test', last_name='Child',
            is_published=True)

    def _upload(self, content, name='photo.jpg', ctype='image/jpeg'):
        f = SimpleUploadedFile(name, content, content_type=ctype)
        return self.client.post(f'/portal/players/{self.player.pk}/photo/',
                                {'file': f})

    def test_text_file_named_jpg_is_rejected(self):
        r = self._upload(b'This is definitely not an image, just text.',
                         name='evil.jpg')
        self.assertEqual(r.status_code, 400)
        self.assertIn('not a readable image', r.content.decode())
        self.player.refresh_from_db()
        self.assertFalse(self.player.photo)

    def test_html_disguised_as_jpg_is_rejected(self):
        r = self._upload(b'<html><script>alert(1)</script></html>',
                         name='evil.jpg')
        self.assertEqual(r.status_code, 400)

    def test_truncated_png_is_rejected(self):
        raw = _png_bytes((600, 400))
        r = self._upload(raw[:len(raw) // 2], name='cut.png',
                         ctype='image/png')
        self.assertEqual(r.status_code, 400)

    def test_svg_is_rejected_even_if_renamed(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'
        r = self._upload(svg, name='vector.jpg')
        self.assertEqual(r.status_code, 400)

    def test_valid_png_is_stored(self):
        r = self._upload(_png_bytes(), name='headshot.png', ctype='image/png')
        self.assertEqual(r.status_code, 200, r.content.decode())
        self.player.refresh_from_db()
        self.assertTrue(self.player.photo.name.endswith('.png'))

    def test_extension_is_corrected_to_real_format(self):
        """PNG bytes uploaded as .jpg must be stored as .png — the served
        content-type must never disagree with the actual bytes."""
        r = self._upload(_png_bytes(), name='actually-png.jpg')
        self.assertEqual(r.status_code, 200)
        self.player.refresh_from_db()
        self.assertTrue(self.player.photo.name.endswith('.png'),
                        self.player.photo.name)

    def test_exif_is_stripped(self):
        """Re-encoding must drop EXIF (orientation/software tags) — the
        same path that removes GPS data when cameras embed it."""
        src = _jpeg_bytes_with_exif()
        self.assertTrue(dict(Image.open(io.BytesIO(src)).getexif()),
                        'test fixture failed to embed EXIF')
        r = self._upload(src, name='tracked.jpg')
        self.assertEqual(r.status_code, 200, r.content.decode())
        self.player.refresh_from_db()
        saved = Image.open(self.player.photo)
        self.assertEqual(dict(saved.getexif()), {})
        self.assertEqual(saved.getexif().get_ifd(0x8825), {})  # no GPS IFD

    def test_anonymous_upload_redirects(self):
        self.client.logout()
        r = self.client.post(f'/portal/players/{self.player.pk}/photo/',
                             {'file': SimpleUploadedFile('x.jpg', _png_bytes(),
                                                         content_type='image/jpeg')})
        self.assertEqual(r.status_code, 302)

    def test_pixel_cap_rejects_huge_images(self):
        """42M pixels is under Pillow's own decompression-bomb guard
        (~89M) but over this app's 40M cap — the app-level check must
        fire before any full decode. A solid-colour PNG this size
        compresses to a few KB on disk."""
        buf = io.BytesIO()
        Image.new('RGB', (7000, 6000), (12, 34, 56)).save(buf, 'PNG')
        self.assertLess(len(buf.getvalue()), 200_000)   # tiny on disk indeed
        r = self._upload(buf.getvalue(), name='huge.png', ctype='image/png')
        self.assertEqual(r.status_code, 400)
        self.assertIn('too large', r.content.decode())
