#!/usr/bin/env python3
"""Cycle P2 seed: demo guardian + announcements board content.

Creates a demo guardian (Mary Chitechi, linked to Victor Chitechi, U15-04)
and a realistic announcement board:
  - 1 PINNED all-squads notice (unread)
  - 1 U15-only notice (unread — proves squad targeting)
  - 2 all-squads notices read by Mary (proves read receipts)
  - 1 FEM-only notice (Mary must NOT see it — proves filtering)
  - 1 unpublished draft (nobody but staff sees it)
Idempotent: wipes announcements + the demo guardian first (like seed-demo-dashboard).

Demo credentials (Phase 0 hardening — no fixed values in source):
  SP_DEMO_PARENT_EMAIL  default demo.parent@example.com (fictional)
  SP_DEMO_PARENT_PASS   random password, generated+displayed once by
                        install.sh; if run by hand without it, a random
                        one is generated and printed here.
"""
import os, secrets, sys
import pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sporting_pearls_backend.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone as tz
from parents.models import (Announcement, AnnouncementRead, Guardian,
                            GuardianPlayer)
from submissions.models import Player

User = get_user_model()

DEMO_EMAIL = (os.environ.get('SP_DEMO_PARENT_EMAIL') or 'demo.parent@example.com').strip().lower()
DEMO_PASS = os.environ.get('SP_DEMO_PARENT_PASS') or ''
if not DEMO_PASS:
    DEMO_PASS = secrets.token_urlsafe(12)
    print(f'[seed] SP_DEMO_PARENT_PASS not set — generated a random demo password: {DEMO_PASS}')

# ── wipe previous demo rows ──────────────────────────────────────────────
AnnouncementRead.objects.all().delete()
Announcement.objects.all().delete()
Guardian.objects.filter(user__username=DEMO_EMAIL).delete()
User.objects.filter(username=DEMO_EMAIL).delete()

victor = Player.objects.filter(ref='U15-04').first()
assert victor, 'Victor Chitechi (U15-04) missing — run import_roster first'
u15, fem = victor.squad, Player.objects.filter(ref='FEM-01').first().squad

now = tz.now()
def days_ago(n):
    return now - tz.timedelta(days=n)

# ── demo guardian ────────────────────────────────────────────────────────
user = User.objects.create_user(username=DEMO_EMAIL,
                                email=DEMO_EMAIL,
                                password=DEMO_PASS,
                                first_name='Mary', last_name='Chitechi')
mary = Guardian.objects.create(user=user, full_name='Mary Chitechi',
                               phone='+254 799 003 521', relation='Mother')
GuardianPlayer.objects.create(guardian=mary, player=victor, is_primary=True)

def ann(title, body, *, squads=None, pinned=False, when, by='Academy Office'):
    a = Announcement.objects.create(
        title=title, body=body, pinned=pinned, is_published=True,
        published_at=when, created_at=when,
        created_by=User.objects.filter(is_superuser=True).first())
    if squads:
        a.squads.set(squads)
    return a

a_info = ann(
    'Parent information evening — the 2026–31 development cycle',
    'Karibu! The academy board invites every parent and guardian to the '
    'information evening on Friday 30 October, 5:30 pm at the Mtwapa '
    'training ground.\n\n'
    'We will walk through the 2026–31 institutional plan: squad pathways '
    'from U9 to U19, the education & life-skills timetable, and how fees '
    'are structured. There will be time for questions with the coaching '
    'staff and the welfare lead.\n\n'
    'Refreshments are provided. Please confirm attendance by replying to '
    'info@sportingpearlsacademy.org or signing the sheet at the gate.',
    pinned=True, when=days_ago(1))

a_u15 = ann(
    'U15 performance squad — extra Tuesday conditioning block',
    'Coach Daniel has added a conditioning block for the U15s every '
    'Tuesday in November, 4:00–5:30 pm at the Pearl Ground, Mtwapa.\n\n'
    'Players should bring water, shin pads and both training kits. '
    'Pick-up remains at 5:45 pm sharp. This block replaces the ordinary '
    'Tuesday session — no extra fee applies.',
    squads=[u15], when=days_ago(2))

a_bus = ann(
    'New bus pick-up point for Mtwapa players',
    'From Saturday, the match-day bus will pick up Mtwapa players at the '
    'new stage opposite Mtambo Mini Market at 7:15 am, ten minutes later '
    'than before.\n\nThe old stop outside the petrol station is closed '
    'for roadworks until further notice.',
    when=days_ago(5))

a_photo = ann(
    'Photos from the Kisauni friendly are ready',
    'The photo team has published 40 pictures from last week\'s friendly '
    'against Kisauni United. A selection now appears on the academy '
    'website squad pages.\n\nFull-resolution copies can be collected on '
    'a USB drive at the office desk during working hours.',
    when=days_ago(8))

a_fem = ann(
    'Féminin — Kilifi Queens away travel list',
    'The travelling squad and travel logistics for the away fixture '
    'against Kilifi Queens have been posted inside the Féminin '
    'whatsapp group. Kit collection is Friday after training.',
    squads=[fem], when=days_ago(3))

draft = Announcement.objects.create(
    title='[Draft] Fee structure revision for 2027 season',
    body='Internal working notes — do not publish until the board signs off.',
    is_published=False)

# Mary has already read the two older all-squads notices
for a in (a_bus, a_photo):
    AnnouncementRead.objects.create(announcement=a, guardian=mary, read_at=days_ago(4))

print(f'seeded: guardian {mary.full_name} -> {victor.ref} ({u15.label})')
print(f'announcements: {Announcement.objects.count()} total '
      f'({Announcement.objects.filter(is_published=True).count()} published) | '
      f'Mary reads: {AnnouncementRead.objects.count()}')
