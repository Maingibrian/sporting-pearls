"""Invite services — the "Approve & invite guardian" machinery.

Shared by the branded portal endpoint (POST /portal/submissions/<ref>/invite/)
and the admin action on submissions. Creates the ParentInvite, emails the
one-time activation link through Resend and returns everything the caller
needs (including the raw link so staff always have a copy-paste fallback).
"""
import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from submissions.views import resend_send

from .models import Guardian, ParentInvite

INVITE_TTL_HOURS = 72

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')

# Payload keys each form uses, tried in order.
GUARDIAN_NAME_KEYS = ('parent_name', 'guardian_name', 'name', 'fullname')
GUARDIAN_PHONE_KEYS = ('parent_phone', 'guardian_phone', 'phone', 'phone_number')
CHILD_NAME_KEYS = ('player_name', 'child_name', 'child', 'name', 'fullname')
SQUAD_HINT_KEYS = ('age_group', 'child_squad', 'squad', 'age_group_or_squad')


def email_from_submission(sub):
    return (sub.email or '').strip()


def prefill_from_submission(sub):
    """Best-effort guardian/child extraction from a submission's answers.

    Returns dict(guardian_name, email, phone, child_name, squad_hint, age).
    form-01/02: name = the child (form-01 carries parent_name separately).
    form-03:    name = the parent, child_name = the child.
    """
    a = sub.payload or {}
    get = lambda keys: next((str(a[k]).strip() for k in keys
                             if a.get(k) and str(a[k]).strip()), '')
    guardian_name = get(('parent_name', 'guardian_name'))
    child_name = get(('player_name', 'child_name'))
    if not guardian_name and not child_name:
        # trial/enquiry style: `name` is whoever filled the form
        child_name = get(('name', 'fullname'))
    elif not guardian_name:
        guardian_name = ''  # staff types it
    phone = get(GUARDIAN_PHONE_KEYS)
    age = ''
    raw_age = get(('age',))
    if raw_age.isdigit():
        age = raw_age
    else:
        dob = get(('dob',))
        m = re.match(r'(\d{4})-(\d{2})-(\d{2})', dob)
        if m:
            today = timezone.localdate()
            age = str(max(0, today.year - int(m.group(1)) -
                          ((today.month, today.day) < (int(m.group(2)), int(m.group(3))))))
    return {
        'guardian_name': guardian_name,
        'email': email_from_submission(sub) or get(('email', 'email_address')),
        'phone': phone,
        'child_name': child_name,
        'squad_hint': get(SQUAD_HINT_KEYS),
        'age': age,
    }


def find_child(name, squad_hint=''):
    """Try to match a child's name to an existing Player profile.
    Exact full-name match first, then a surname match inside the hinted squad."""
    from submissions.models import Player
    name = (name or '').strip()
    if not name:
        return None
    parts = name.split()
    qs = Player.objects.select_related('squad')
    for p in qs:
        full = f'{p.first_name} {p.last_name}'.strip().lower()
        if full == name.lower():
            return p
    last = parts[-1]
    qs2 = qs.filter(last_name__icontains=last)
    if squad_hint:
        hinted = [p for p in qs2
                  if squad_hint.lower() in p.squad.label.lower()
                  or squad_hint.lower() in p.squad.code.lower()]
        if hinted:
            return hinted[0]
    return qs2.first() or None


def next_free_ref(squad):
    from submissions.models import Player
    existing = set(Player.objects.filter(squad=squad).values_list('ref', flat=True))
    n = 1
    while f'{squad.code}-{n:02d}' in existing:
        n += 1
    return f'{squad.code}-{n:02d}'


def create_player_from_application(child_name, squad, age=None, position=''):
    """Approving an application that has no player profile yet → make a
    draft player row (never auto-published; coach reviews it first)."""
    from submissions.models import Player
    parts = (child_name or '').strip().split()
    first = parts[0][:60] if parts else 'New'
    last = ' '.join(parts[1:])[:60] if len(parts) > 1 else '—'
    return Player.objects.create(
        squad=squad, ref=next_free_ref(squad), first_name=first, last_name=last,
        age=int(age) if age else None, position=position or '',
        is_published=False, pitch_order=12,
    )


def guard_existing_account(email):
    """Refuse invites that collide with users we cannot safely create."""
    User = get_user_model()
    user = User.objects.filter(username__iexact=email).first()
    if user is None:
        return None
    if Guardian.objects.filter(user=user).exists():
        return 'A parent account already exists for this email — they can sign in directly.'
    return ('This email is already used by another account '
            '(staff or admin). Use a different guardian email.')


def activation_url(request, token):
    from django.urls import reverse
    return request.build_absolute_uri(reverse('parents-activate', args=[token]))


def invite_email_payload(url, guardian_name, child_phrase):
    """Multipart (html + text) invitation email — branded, with signature.
    Shared by the portal endpoint and the admin re-send action."""
    from submissions.email_branding import invite_email_payload as _payload
    return _payload(url, guardian_name, child_phrase)


def create_and_send_invite(*, guardian_name, email, relation='Guardian',
                           player=None, invited_by=None, submission=None,
                           request=None):
    """Create the invite row and email the link. Returns (invite, ok, detail).
    `detail` is the email delivery note; `invite.invite_url` carries the link."""
    email = (email or '').strip().lower()
    m = EMAIL_RE.fullmatch(email)
    if not m:
        return None, False, 'That email address does not look right.'
    guardian_name = (guardian_name or '').strip()
    if not guardian_name:
        return None, False, 'Guardian name is required.'

    clash = guard_existing_account(email)
    if clash:
        return None, False, clash

    # One active invite per email — avoid stacking live links.
    live = ParentInvite.objects.filter(email=email, accepted_at__isnull=True,
                                       expires_at__gt=timezone.now()).first()
    if live:
        return live, False, (f'An active invite already exists for this email '
                             f'(expires {timezone.localtime(live.expires_at):%d %b %Y %H:%M}).')

    child_phrase = ''
    if player is not None:
        child_phrase = f"your child {player.first_name}'s "
    invite = ParentInvite.objects.create(
        email=email, guardian_name=guardian_name[:120], relation=relation or 'Guardian',
        player=player, invited_by=invited_by, submission=submission,
        token=secrets.token_urlsafe(24),
        expires_at=timezone.now() + timezone.timedelta(hours=INVITE_TTL_HOURS),
    )
    url = activation_url(request, invite.token) if request is not None else f'/portal/parents/activate/{invite.token}/'
    invite.invite_url = url

    payload = invite_email_payload(url, guardian_name, child_phrase)
    payload.update({'from': settings.EMAIL_FROM, 'to': [email]})
    ok, detail = resend_send(payload)
    invite.email_status = ('sent' if ok else detail)[:32]
    invite.email_error = '' if ok else detail
    invite.save(update_fields=['email_status', 'email_error'])
    return invite, ok, detail
