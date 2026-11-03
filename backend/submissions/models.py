"""Data model: a ledger for every form submission + fixtures the homepage
can render once published from the admin + the six academy squads' rosters
(the Player Profile Manager — what the-squad page renders live).

Phase 1 adds the restricted safeguarding store: form-10 reports live in
their own permission-gated model (SafeguardingReport) with an immutable
audit trail (SafeguardingAuditEntry), never in the shared ledger. See
submissions/safeguarding.py for the roles and parsing rules."""
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from .safeguarding import SAFEGUARDING_STATUS

STATUS_CHOICES = [
    ('new', 'New'),
    ('reviewed', 'Reviewed'),
    ('archived', 'Archived'),
]

SIDE_CHOICES = [
    ('home', 'Home'),
    ('away', 'Away'),
]

# The 17 tactical position codes used across the site, the paper form
# and the admin. Order mirrors the printed legend on the data form.
POSITIONS = [
    ('GK', 'Goalkeeper'),
    ('RB', 'Right Back'),
    ('CB', 'Centre Back'),
    ('LB', 'Left Back'),
    ('DM', 'Defensive Midfielder'),
    ('CM', 'Central Midfielder'),
    ('RM', 'Right Midfielder'),
    ('LM', 'Left Midfielder'),
    ('AM', 'Attacking Midfielder'),
    ('RAM', 'Right Attacking Midfielder'),
    ('CAM', 'Central Attacking Midfielder'),
    ('LAM', 'Left Attacking Midfielder'),
    ('RW', 'Right Winger'),
    ('LW', 'Left Winger'),
    ('RWB', 'Right Wing-Back'),
    ('LWB', 'Left Wing-Back'),
    ('ST', 'Striker'),
]

FORMATIONS = [
    ('4-3-3', '4-3-3'),
    ('4-4-2', '4-4-2'),
    ('4-2-3-1', '4-2-3-1'),
    ('3-5-2', '3-5-2'),
]


class CoachPhotoStorage(FileSystemStorage):
    """Storage that re-encodes coach photos on EVERY save path (Phase 4).

    The academy manages coaching staff from the Django admin, so the
    upload can arrive through any writer (admin form, shell, future
    views). Whatever writes the file, only a clean Pillow re-encode is
    ever stored: EXIF/GPS/ICC metadata never lands in /media/, the
    stored extension always matches the real image format, and the
    pixel-count cap rejects decompression bombs before the full decode.
    Invalid inputs raise ValueError — the write fails closed.
    """

    def _save(self, name, content):
        import io
        from django.core.files.base import ContentFile
        from django.utils.text import get_valid_filename
        from PIL import Image

        raw = content.read()
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw))
            if (img.width or 0) * (img.height or 0) > 40_000_000:
                raise ValueError('image exceeds the 40-megapixel cap')
            img.load()
        except Exception:
            raise ValueError('coach photo is not a readable image')
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('coach photo must be JPG, PNG or WebP')
        buf = io.BytesIO()
        if fmt == 'JPEG':
            img.convert('RGB').save(buf, 'JPEG', quality=85)
            ext = '.jpg'
        elif fmt == 'PNG':
            img.save(buf, 'PNG')
            ext = '.png'
        else:
            img.save(buf, 'WEBP', quality=85)
            ext = '.webp'
        stem = name.rsplit('/', 1)[-1].rsplit('.', 1)[0] or 'coach'
        name = 'coaches/coach-' + get_valid_filename(stem) + ext
        return super()._save(name, ContentFile(buf.getvalue()))


class FormSubmission(models.Model):
    ref = models.CharField('reference', max_length=40, unique=True)
    form_slug = models.CharField('form', max_length=80, db_index=True)
    name = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=320, blank=True)
    payload = models.JSONField('answers', default=dict)
    email_status = models.CharField(max_length=32, default='pending')
    email_error = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='new', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'submission'

    def __str__(self):
        return f'{self.ref} · {self.form_slug}'


class Fixture(models.Model):
    team = models.CharField('Sporting Pearls team', max_length=80,
                            help_text="e.g. Sporting Pearls U17, SP Féminin, U15")
    opponent = models.CharField(max_length=80)
    competition = models.CharField(max_length=120, blank=True)
    date = models.DateField()
    kickoff = models.CharField('kick-off', max_length=20, blank=True,
                               help_text='e.g. 15:00 — leave blank for TBC')
    venue = models.CharField(max_length=120, blank=True)
    home_away = models.CharField(max_length=4, choices=SIDE_CHOICES, default='home')
    is_published = models.BooleanField(
        'published on homepage', default=False,
        help_text='Published fixtures replace the "Coming Soon" panel on the homepage.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date']
        verbose_name = 'fixture'
        verbose_name_plural = 'fixtures'

    def __str__(self):
        return f'{self.team} vs {self.opponent} · {self.date:%d %b %Y}'


class Result(models.Model):
    """A played match with its score — the Results page content (Phase 7).

    Admin-settable exactly like fixtures: the academy office enters
    finished matches from the Django admin, and published results
    replace the website results page's "Coming Soon" panel
    automatically. Nothing is fabricated — an empty list keeps the
    honest Coming Soon state."""
    team = models.CharField('Sporting Pearls team', max_length=80,
                            help_text="e.g. Sporting Pearls U17, SP Féminin, U15")
    opponent = models.CharField(max_length=80)
    competition = models.CharField(max_length=120, blank=True)
    date = models.DateField()
    venue = models.CharField(max_length=120, blank=True)
    home_away = models.CharField(max_length=4, choices=SIDE_CHOICES, default='home')
    our_score = models.PositiveSmallIntegerField('our score')
    their_score = models.PositiveSmallIntegerField('their score')
    report = models.TextField('short match report', blank=True,
                              help_text='Optional 2-3 sentence summary shown under the score.')
    is_published = models.BooleanField('published on results page', default=False,
                                       help_text='Published results replace the "Coming Soon" panel on the results page.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name = 'result'
        verbose_name_plural = 'results'

    def __str__(self):
        return f'{self.team} {self.our_score}–{self.their_score} {self.opponent} · {self.date:%d %b %Y}'

    @property
    def outcome(self):
        """W / D / L from the academy's point of view."""
        if self.our_score > self.their_score:
            return 'W'
        if self.our_score < self.their_score:
            return 'L'
        return 'D'


class Squad(models.Model):
    """One of the academy teams. `key` must match the site's tab key
    (feminin, u9, u13, u15, u17, u19); `code` is the short code printed on
    the paper data form (FEM, U09, ...)."""
    key = models.CharField('site key', max_length=10, unique=True,
                           help_text='Must match the website tab key, e.g. feminin, u9, u13, u15, u17, u19.')
    code = models.CharField('short code', max_length=4, unique=True,
                            help_text='Printed on the paper data form, e.g. FEM, U09.')
    label = models.CharField(max_length=80, help_text='e.g. Sporting Pearls Féminin, U9 Foundation Squad')
    formation = models.CharField(max_length=8, choices=FORMATIONS, default='4-3-3')
    accent = models.CharField('accent colour', max_length=9, default='#f59d1e',
                              help_text='Hex colour used on the website squad tab, e.g. #f59d1e')
    sort = models.PositiveSmallIntegerField('display order', default=0)

    class Meta:
        ordering = ['sort']
        verbose_name = 'squad'

    def __str__(self):
        return self.label


class Player(models.Model):
    """A registered player — the data the paper collection form gathers.
    Published players appear on the website squad pages automatically."""
    squad = models.ForeignKey(Squad, on_delete=models.CASCADE, related_name='players')
    ref = models.CharField('reference code', max_length=12, unique=True,
                           help_text='Pre-printed on the paper form, e.g. FEM-01. Keep it — it maps the sheet to this profile.')
    number = models.PositiveSmallIntegerField('shirt number', null=True, blank=True)
    first_name = models.CharField(max_length=60)
    last_name = models.CharField(max_length=60)
    position = models.CharField(max_length=4, choices=POSITIONS, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    height_m = models.CharField('height (m)', max_length=6, blank=True,
                                help_text='e.g. 1.68')
    foot = models.CharField(max_length=1, choices=[('R', 'Right'), ('L', 'Left')], blank=True)
    motto = models.TextField('player motto', blank=True,
                             help_text='The quote shown on the player card.')
    photo = models.ImageField(upload_to='players/', blank=True,
                              help_text='Upload the scanned photo from the data form. Overrides the URL below.')
    photo_url = models.CharField('photo URL', max_length=300, blank=True,
                                 help_text='Optional: path on the website, e.g. Pearls/FEMALE/headshot.jpg')
    is_captain = models.BooleanField('captain', default=False)
    is_published = models.BooleanField('published on website', default=False,
                                       help_text='Only published players appear on the squad pages.')
    pitch_order = models.PositiveSmallIntegerField(
        'pitch slot', default=0,
        help_text='Position in the starting shape, 1–11 (1 = goalkeeper). Spares: leave 0 or 12+.')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['squad__sort', 'pitch_order', 'ref']
        verbose_name = 'player'
        indexes = [models.Index(fields=['squad', 'pitch_order'])]

    def __str__(self):
        return f'{self.ref} · {self.first_name} {self.last_name}'


class Coach(models.Model):
    """A member of the academy's coaching / technical staff (Phase 4).

    Admin-settable content: the academy office publishes the technical
    team from the Django admin — name, role, an optional squad link, a
    short bio and a photo. Only published coaches are exposed by the
    public /api/coaches/ endpoint and rendered on the website's
    technical-team section. Coach photos follow the player-photo rules:
    verified with Pillow, re-encoded with EXIF/GPS stripped, pixel-
    capped, and served through the authenticated media gate (public
    only while the coach is published).
    """
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120,
                            help_text='e.g. Head Coach · U15 Lead Coach · Goalkeeper Coach · Fitness & Conditioning')
    squad = models.ForeignKey(Squad, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='coaches',
                              help_text='Optional: the squad this coach primarily works with.')
    bio = models.TextField(blank=True,
                           help_text='One or two sentences shown on the website card.')
    photo = models.ImageField(upload_to='coaches/', storage=CoachPhotoStorage(),
                              blank=True,
                              help_text='JPG, PNG or WebP. Re-encoded on save — hidden metadata is stripped.')
    is_published = models.BooleanField('published on website', default=False,
                                       help_text='Only published coaches appear on the website.')
    sort = models.PositiveSmallIntegerField('display order', default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort', 'name']
        verbose_name = 'coach'

    def __str__(self):
        return f'{self.name} · {self.role}'


class FemininGalleryStorage(FileSystemStorage):
    """Storage that re-encodes Féminin gallery photos on EVERY save path.

    The 'On the Pitch' gallery on the Féminin page ships hidden and only
    appears once the academy publishes REAL photos of the girls' programme
    from the Django admin (rev 25). Whatever writes the file — admin form,
    shell, future views — only a clean Pillow re-encode is ever stored:
    EXIF/GPS/ICC metadata never lands in /media/, the stored extension
    always matches the real image format, and the pixel-count cap rejects
    decompression bombs before the full decode. Invalid inputs raise
    ValueError — the write fails closed."""

    def _save(self, name, content):
        import io
        from django.core.files.base import ContentFile
        from django.utils.text import get_valid_filename
        from PIL import Image

        raw = content.read()
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw))
            if (img.width or 0) * (img.height or 0) > 40_000_000:
                raise ValueError('image exceeds the 40-megapixel cap')
            img.load()
        except Exception:
            raise ValueError('gallery photo is not a readable image')
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('gallery photo must be JPG, PNG or WebP')
        buf = io.BytesIO()
        if fmt == 'JPEG':
            img.convert('RGB').save(buf, 'JPEG', quality=85)
            ext = '.jpg'
        elif fmt == 'PNG':
            img.save(buf, 'PNG')
            ext = '.png'
        else:
            img.save(buf, 'WEBP', quality=85)
            ext = '.webp'
        stem = name.rsplit('/', 1)[-1].rsplit('.', 1)[0] or 'photo'
        name = 'gallery/feminin/fg-' + get_valid_filename(stem) + ext
        return super()._save(name, ContentFile(buf.getvalue()))


class FemininGalleryPhoto(models.Model):
    """A real photograph of the girls' programme for the Féminin page.

    The 'On the Pitch' gallery section ships HIDDEN on the static site —
    it renders only when this model has published rows, i.e. when the
    academy has uploaded real photos from the backend (rev 25). Until
    then the section stays off the page entirely: no stock stand-ins for
    the girls' team. Photos follow the player/coach photo rules —
    Pillow-verified, re-encoded with EXIF/GPS stripped, pixel-capped and
    served through the authenticated media gate (public only while the
    photo is published)."""

    caption = models.CharField(max_length=120, blank=True,
                               help_text='Short label shown on the tile, e.g. "Pass & move".')
    alt = models.CharField('alt text', max_length=250, blank=True,
                           help_text='Describe the photo for screen readers — who, what, where.')
    photo = models.ImageField(upload_to='gallery/feminin/',
                              storage=FemininGalleryStorage(),
                              help_text='JPG, PNG or WebP. Re-encoded on save — hidden metadata is stripped.')
    is_published = models.BooleanField('published on website', default=False,
                                       help_text='The gallery section appears on the Féminin page only when at least one photo is published.')
    sort = models.PositiveSmallIntegerField('display order', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort', 'id']
        verbose_name = 'Féminin gallery photo'

    def __str__(self):
        label = self.caption or 'Untitled photo'
        state = 'live' if self.is_published else 'draft'
        return f'{label} ({state})'


class SafeguardingReport(models.Model):
    """A child-welfare / safeguarding concern raised through form 10.

    The most restricted data in the system: visible ONLY to users granted
    the DSO role (see safeguarding.DSO_GROUP). Never emailed in full,
    never listed in the staff ledger, never exported. Every access and
    status change is written to SafeguardingAuditEntry.
    """
    STATUS = SAFEGUARDING_STATUS

    ref = models.CharField('reference', max_length=40, unique=True)
    reporter_preference = models.CharField(
        'reporting preference', max_length=20,
        choices=[('confidential', 'Confidential (identity known to DSO)'),
                 ('anonymous', 'Completely anonymous')],
        default='confidential')
    reporter_name = models.CharField('reporter name', max_length=300, blank=True)
    reporter_role = models.CharField('reporter role', max_length=300, blank=True)
    reporter_contact = models.CharField('reporter phone', max_length=300, blank=True)
    reporter_email = models.CharField('reporter email', max_length=320, blank=True)
    child_name = models.CharField('child / player', max_length=300, blank=True)
    child_age = models.CharField('estimated age / DOB', max_length=300, blank=True)
    squad = models.CharField('squad tier', max_length=300, blank=True)
    categories = models.TextField('incident categories', blank=True,
                                  help_text='Canonical labels, semicolon-separated.')
    persons_in_question = models.CharField('persons whose conduct is in question',
                                           max_length=300, blank=True)
    incident_date = models.CharField('date of incident', max_length=300, blank=True)
    incident_time = models.CharField('approximate time', max_length=300, blank=True)
    location = models.CharField('specific location', max_length=300, blank=True)
    narrative = models.TextField('factual description', blank=True)
    witnesses = models.CharField('witnesses', max_length=300, blank=True)
    disclosure_history = models.CharField('disclosed to others', max_length=300, blank=True)
    external_authority = models.CharField('external authority notified', max_length=300, blank=True)
    police_ob = models.CharField('OB / police reference', max_length=300, blank=True)
    extra = models.JSONField('additional answers', default=dict, blank=True)

    # Submission metadata (kept for the DSO's investigation, never shown
    # to non-DSO staff).
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    email_status = models.CharField('DSO notification', max_length=32, default='pending')
    email_error = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS, default='received', db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='safeguarding_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'safeguarding report'
        verbose_name_plural = 'safeguarding reports'
        permissions = [
            ('view_safeguardingreport_restricted', 'Can view safeguarding reports (DSO store)'),
        ]

    def __str__(self):
        return f'{self.ref} ({self.get_status_display()})'


class SafeguardingAuditEntry(models.Model):
    """Append-only access & action log for the safeguarding store.

    Written by the public API (report received, notification sent) and by
    the DSO desk (viewed, status changed, note added, assigned). Instance
    save() on an existing row and delete() both raise, so the application
    layer can never rewrite history. Residual risk: direct database file
    access — see SAFEGUARDING-RUNBOOK.md (break-glass & retention).
    """
    ACTION_CHOICES = [
        ('received', 'Report received'),
        ('viewed', 'Viewed by DSO'),
        ('status_changed', 'Status changed'),
        ('assigned', 'Assigned'),
        ('note_added', 'Case note added'),
        ('notified', 'DSO notified by email'),
        ('migrated', 'Migrated from legacy ledger'),
    ]

    report = models.ForeignKey(SafeguardingReport, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='audit_entries')
    report_ref = models.CharField('report reference', max_length=40, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='safeguarding_audit')
    actor_username = models.CharField('actor (username snapshot)', max_length=150)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'safeguarding audit entry'
        verbose_name_plural = 'safeguarding audit entries'

    def __str__(self):
        return f'{self.created_at:%d %b %H:%M} · {self.action} · {self.report_ref}'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError('Safeguarding audit entries are append-only.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError('Safeguarding audit entries are immutable.')
