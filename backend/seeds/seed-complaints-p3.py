#!/usr/bin/env python3
"""Cycle P3 seed — demo complaints for the welfare desk.

Creates three backdated cases for the demo family (Mary Chitechi, whose
child is Victor Chitechi U15-04) with a realistic staff thread, including
one internal note. Idempotent: skips if the demo cases already exist.

Run:  .venv/bin/python manage.py shell < scripts/seed-complaints-p3.py
or:   sp-backend/.venv/bin/python (dev path removed)
"""
import os
import sys
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sporting_pearls_backend.settings')
import pathlib as _pl
sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import django  # noqa: E402
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

from parents.models import Complaint, ComplaintReply, Guardian  # noqa: E402

now = timezone.now()
admin = get_user_model().objects.filter(username='admin').first()
mary = Guardian.objects.filter(full_name='Mary Chitechi').first()
if mary is None:
    sys.exit('Demo guardian Mary Chitechi not found — run seed-announcements-p2.py first.')
victor = mary.links.select_related('player').first().player if mary.links.exists() else None

if Complaint.objects.filter(guardian=mary).exists():
    print(f'Complaints for {mary.full_name} already exist — nothing to seed.')
    sys.exit(0)

# ── Case 1: resolved, full thread with an internal note ──────────────────
c1 = Complaint.objects.create(
    guardian=mary, player=victor, category='facilities',
    subject='Torn goal net on the main training pitch',
    message=('Good morning. I watched Tuesday\u2019s session and the goal net on the '
             'main pitch has a large tear on the near side. The balls keep rolling '
             'through and the boys lose training time fetching them. Could the academy '
             'please repair or replace it before the next match?'),
    status='resolved', assigned_to=admin)
c1.created_at = c1.updated_at = now - timedelta(days=12)
c1.save()
ComplaintReply.objects.create(
    complaint=c1, by_staff=admin,
    body=('Karibu Mary, and thank you for flagging this — sharp eyes! Our grounds '
          'team inspected the net the same afternoon and re-strung the torn panel.\n\n'
          'The repair held through the weekend session, and we have added a net check '
          'to the weekly pitch checklist so it does not sneak up on us again. Asante '
          'for looking out for the squad.'))
ComplaintReply.objects.create(
    complaint=c1, by_staff=admin,
    body=('Sourcing quotes for a brand-new net anyway — budget line approved next '
          'month. Do NOT mention the budget bit to parents yet.'),
    is_internal=True)
for r in c1.replies.all():
    r.created_at = c1.created_at + timedelta(days=1)
    r.save()
c1.status = 'resolved'
c1.updated_at = c1.created_at + timedelta(days=2)
c1.save()

# ── Case 2: open, no reply yet — this is what staff see waiting ──────────
c2 = Complaint.objects.create(
    guardian=mary, player=victor, category='fees',
    subject='Clarify the November training fee invoice',
    message=('Hello. The November fee SMS mentions a "kit maintenance top-up" of KSh '
             '1,500 that was not part of the fee structure shared at the start of the '
             'season. Could someone explain what it covers and whether it applies to '
             'every squad? I want to plan ahead before the due date. Thank you.'),
    status='open')
c2.created_at = c2.updated_at = now - timedelta(days=1, hours=3)
c2.save()

# ── Case 3: closed, older transport matter ───────────────────────────────
c3 = Complaint.objects.create(
    guardian=mary, player=None, category='transport',
    subject='Away-fixture bus returned late to Mtwapa',
    message=('On the 12th the away bus back from the Mombasa fixture arrived almost '
             'ninety minutes late and the driver\u2019s phone was off, so several of us '
             'waited at the stage with no information. It would help a lot if the team '
             'manager could send a short update message when the bus is delayed.'),
    status='closed', assigned_to=admin)
c3.created_at = c3.updated_at = now - timedelta(days=26)
c3.save()
ComplaintReply.objects.create(
    complaint=c3, by_staff=admin,
    body=('Dear Mary, we are sorry — that wait was our failure and we have apologised '
          'to the families affected. The delay came from a breakdown on the highway.\n\n'
          'Two changes are now in place: the team manager sends a broadcast SMS the '
          'moment a return leg is delayed by more than fifteen minutes, and every bus '
          'carries a charged academy phone whose number is shared before departure.'))
c3.replies.update(created_at=c3.created_at + timedelta(days=1))
c3.status = 'closed'
c3.updated_at = c3.created_at + timedelta(days=2)
c3.save()

print('Seeded 3 demo complaints for Mary Chitechi:')
for c in Complaint.objects.filter(guardian=mary):
    print(f'  #{c.id} [{c.status}] {c.subject} — {c.replies.count()} replies')
