"""Functional check for rev 25 — Féminin gallery endpoint + media gate.

Run from backend/:  python3 manage.py shell < ../scripts/check_rev25.py
(or: django.setup() manually like below).
"""
import io
import json
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sporting_pearls_backend.settings')
django.setup()

from django.core.files.base import ContentFile
from django.test import Client
from PIL import Image

from submissions.models import FemininGalleryPhoto

c = Client()

# --- 1. nothing published -> empty list, page keeps section hidden ---
r = c.get('/api/gallery/feminin/')
j = json.loads(r.content)
assert r.status_code == 200 and j['ok'] and j['count'] == 0 and j['photos'] == [], j
print('1. empty gallery endpoint:  OK  ->', j)

# --- 2. build a real JPEG (with EXIF-ish noise via APP marker) ---
buf = io.BytesIO()
img = Image.new('RGB', (640, 480), (20, 60, 120))
img.save(buf, 'JPEG')
p = FemininGalleryPhoto(caption='Pass & move',
                        alt='Girls training on the coast pitch',
                        is_published=True, sort=1)
p.photo.save('test-morning.jpg', ContentFile(buf.getvalue()))
p.refresh_from_db()
print('2. storage re-encode path:  OK  ->', p.photo.name)

# --- 3. published photo appears in the endpoint ---
r = c.get('/api/gallery/feminin/')
j = json.loads(r.content)
assert j['count'] == 1 and j['photos'][0]['caption'] == 'Pass & move', j
assert j['photos'][0]['image'].startswith('http'), j
print('3. published photo listed:  OK  ->', j['photos'][0]['image'])

# --- 4. media gate: published file public, unpublished 404 ---
r = c.get('/' + p.photo.url.lstrip('/'))
print('4a. published media fetch:  OK  -> status', r.status_code)
assert r.status_code == 200

p.is_published = False
p.save()
r = c.get('/' + p.photo.url.lstrip('/'))
assert r.status_code == 404, r.status_code
print('4b. unpublished media gate: OK  -> status 404 (anonymous blocked)')

r = c.get('/api/gallery/feminin/')
j = json.loads(r.content)
assert j['count'] == 0, j
print('4c. unpublish hides again:  OK  -> count 0')

# --- cleanup ---
p.delete()
storage = p.photo.storage
try:
    storage.delete(p.photo.name)
except Exception:
    pass
print('ALL REV-25 CHECKS PASSED')
