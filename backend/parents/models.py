"""Parent accounts — the data behind the Parent Portal.

Flow: a staff member approves an application ("Approve & invite guardian"),
an email with a one-time activation link goes out, the parent sets a
password and lands in the branded portal at /portal/parents/.

Guardians are linked to Players (children) through GuardianPlayer — every
parent-facing query is filtered through that link table, so a parent can
only ever see their own children. Announcement / Complaint models ship now
so the schema is stable; the P2/P3 cycles light them up.
"""
from django.conf import settings
from django.db import models

RELATION_CHOICES = [
    ('Mother', 'Mother'),
    ('Father', 'Father'),
    ('Guardian', 'Guardian'),
    ('Other', 'Other (aunt, uncle, sponsor…)'),
]

COMPLAINT_CATEGORIES = [
    ('coaching', 'Coaching & Training'),
    ('fees', 'Fees & Payments'),
    ('facilities', 'Facilities & Grounds'),
    ('scheduling', 'Fixtures & Scheduling'),
    ('welfare', 'Welfare & Safeguarding'),
    ('transport', 'Transport & Travel'),
    ('other', 'Something else'),
]

COMPLAINT_STATUS = [
    ('open', 'Open'),
    ('in_review', 'In review'),
    ('resolved', 'Resolved'),
    ('closed', 'Closed'),
]


class Guardian(models.Model):
    """One parent/guardian account. 1:1 with the Django user (email login)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='guardian_profile')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40, blank=True)
    relation = models.CharField(max_length=12, choices=RELATION_CHOICES, default='Guardian')
    is_active = models.BooleanField(
        'account active', default=True,
        help_text='Switch off to revoke portal access instantly (the account and its history are kept).')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'guardian account'

    def __str__(self):
        return f'{self.full_name} ({self.user.get_username()})'


class GuardianPlayer(models.Model):
    """Link table guardian ↔ child. Siblings = several rows for one guardian."""
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='links')
    player = models.ForeignKey('submissions.Player', on_delete=models.CASCADE,
                               related_name='guardian_links')
    is_primary = models.BooleanField('primary contact', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('guardian', 'player')]
        ordering = ['player__squad__sort', 'player__ref']
        verbose_name = 'guardian–child link'

    def __str__(self):
        return f'{self.guardian.full_name} → {self.player}'


class ParentInvite(models.Model):
    """One-time activation link emailed to an approved guardian (72 h)."""
    email = models.EmailField()
    guardian_name = models.CharField(max_length=120)
    relation = models.CharField(max_length=12, choices=RELATION_CHOICES, default='Guardian')
    player = models.ForeignKey('submissions.Player', null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='invites',
                               help_text='The child this account is about.')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='parent_invites')
    submission = models.ForeignKey('submissions.FormSubmission', null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='invites')
    email_status = models.CharField(max_length=32, default='pending')
    email_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'parent invite'

    def __str__(self):
        return f'{self.email} → {self.player or "?"}'

    @property
    def is_accepted(self):
        return self.accepted_at is not None

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at <= timezone.now()

    @property
    def is_usable(self):
        return not self.is_accepted and not self.is_expired


class Announcement(models.Model):
    """A notice from the academy. Empty squads = everyone; otherwise only the
    linked squads' parents see it. (Parent-facing board arrives in P2.)"""
    title = models.CharField(max_length=150)
    body = models.TextField()
    squads = models.ManyToManyField('submissions.Squad', blank=True,
                                    related_name='announcements',
                                    help_text='Leave empty to reach every parent.')
    is_published = models.BooleanField(default=False)
    pinned = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='announcements')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-pinned', '-published_at', '-created_at']
        verbose_name = 'announcement'

    def __str__(self):
        return self.title


class AnnouncementRead(models.Model):
    """Read receipts — powers the parents' unread badge."""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE,
                                     related_name='reads')
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE,
                                 related_name='reads')
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('announcement', 'guardian')]
        verbose_name = 'announcement read receipt'


class Complaint(models.Model):
    """A private case between one guardian and the academy."""
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='complaints')
    player = models.ForeignKey('submissions.Player', null=True, blank=True,
                               on_delete=models.SET_NULL, related_name='complaints')
    category = models.CharField(max_length=20, choices=COMPLAINT_CATEGORIES, default='other')
    subject = models.CharField(max_length=150)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=COMPLAINT_STATUS, default='open', db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='complaints')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'complaint'

    def __str__(self):
        return f'#{self.id} {self.subject} ({self.status})'


class ComplaintReply(models.Model):
    """Thread message on a complaint. `is_internal` notes are staff-only and
    are never serialized into parent-facing responses."""
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name='replies')
    by_staff = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name='complaint_replies')
    by_guardian = models.ForeignKey(Guardian, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='complaint_replies')
    body = models.TextField()
    is_internal = models.BooleanField('internal note (never shown to the parent)', default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'complaint reply'
