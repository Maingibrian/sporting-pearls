"""Admin dashboard: review submissions (search/filter/CSV export) and
manage fixtures that appear on the homepage + the Player Profile Manager
(six squads' rosters, published straight to the website).

Phase 1: the restricted safeguarding store. SafeguardingReport and
SafeguardingAuditEntry are registered but visible ONLY to users granted
the DSO role — the checks deliberately exclude superusers who have not
been granted the role (break-glass = temporarily add the DSO group; see
SAFEGUARDING-RUNBOOK.md). Reports are read-only in the admin (the DSO
desk is the working surface) and can never be added or deleted here."""
import csv
import json

from django.contrib import admin
from django import forms
from django.http import HttpResponse
from django.utils.html import format_html

from .models import (Coach, FemininGalleryPhoto, Fixture, FormSubmission,
                     Player, Result, SafeguardingAuditEntry,
                     SafeguardingReport, Squad)
from .safeguarding import is_dso


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ('ref', 'form_slug', 'name', 'email', 'status',
                    'email_status', 'created_at')
    list_filter = ('form_slug', 'status', 'email_status', 'created_at')
    search_fields = ('ref', 'name', 'email', 'payload')
    readonly_fields = ('ref', 'form_slug', 'name', 'email', 'payload_pretty',
                       'email_status', 'email_error', 'ip', 'user_agent', 'created_at')
    date_hierarchy = 'created_at'
    list_per_page = 50
    actions = ('export_csv', 'mark_reviewed', 'mark_archived')

    @admin.display(description='answers')
    def payload_pretty(self, obj):
        pretty = json.dumps(obj.payload, indent=2, ensure_ascii=False)
        return format_html('<pre style="white-space:pre-wrap">{}</pre>', pretty)

    @admin.action(description='Mark selected as reviewed')
    def mark_reviewed(self, request, queryset):
        queryset.update(status='reviewed')

    @admin.action(description='Mark selected as archived')
    def mark_archived(self, request, queryset):
        queryset.update(status='archived')

    @admin.action(description='Export selected to CSV')
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=submissions.csv'
        writer = csv.writer(response)
        writer.writerow(['ref', 'form', 'name', 'email', 'status',
                         'email_status', 'created_at', 'answers_json'])
        for obj in queryset:
            writer.writerow([obj.ref, obj.form_slug, obj.name, obj.email,
                             obj.status, obj.email_status,
                             obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                             json.dumps(obj.payload, ensure_ascii=False)])
        return response

    def has_add_permission(self, request):
        return False  # ledger rows only come from the API


@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ('team', 'opponent', 'competition', 'date', 'kickoff',
                    'venue', 'home_away', 'is_published')
    list_filter = ('is_published', 'home_away', 'date')
    list_editable = ('is_published',)
    search_fields = ('team', 'opponent', 'competition', 'venue')
    list_per_page = 50


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ('team', 'opponent', 'our_score', 'their_score',
                    'competition', 'date', 'venue', 'home_away', 'is_published')
    list_filter = ('is_published', 'home_away', 'date')
    list_editable = ('is_published',)
    search_fields = ('team', 'opponent', 'competition', 'venue')
    list_per_page = 50
    date_hierarchy = 'date'


# ── Player Profile Manager ──────────────────────────────────────────────

@admin.register(Squad)
class SquadAdmin(admin.ModelAdmin):
    list_display = ('label', 'code', 'key', 'formation', 'accent',
                    'player_count', 'sort')
    list_editable = ('formation', 'sort')
    search_fields = ('label', 'code', 'key')
    list_per_page = 20

    @admin.display(description='players')
    def player_count(self, obj):
        n = obj.players.count()
        pub = obj.players.filter(is_published=True).count()
        return format_html('{} <span style="color:#8a94a6">({} live)</span>', n, pub)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('thumb', 'ref', 'squad', 'number', 'first_name',
                    'last_name', 'position', 'age', 'height_m', 'foot',
                    'is_captain', 'is_published')
    list_filter = ('squad', 'position', 'is_published', 'is_captain')
    search_fields = ('ref', 'first_name', 'last_name', 'motto')
    list_editable = ('number', 'position', 'is_published')
    list_select_related = ('squad',)
    ordering = ('squad__sort', 'pitch_order', 'ref')
    list_per_page = 50
    actions = ('publish_players', 'unpublish_players')
    fieldsets = (
        ('Identity', {
            'fields': ('squad', 'ref', 'first_name', 'last_name', 'number',
                       'is_captain', 'is_published', 'pitch_order'),
        }),
        ('Playing profile', {
            'fields': ('position', 'age', 'height_m', 'foot'),
        }),
        ('Photo & motto', {
            'fields': ('photo', 'photo_url', 'motto'),
        }),
    )

    @admin.display(description='photo')
    def thumb(self, obj):
        if obj.photo:
            try:
                return format_html(
                    '<img src="{}" style="width:42px;height:42px;border-radius:9px;'
                    'object-fit:cover" alt=""/>', obj.photo.url)
            except ValueError:
                pass
        return format_html(
            '<span style="display:inline-grid;place-items:center;width:42px;height:42px;'
            'border-radius:9px;background:#eef0f3;color:#5c6a7e;font-weight:700;'
            'font-size:11px">{}</span>', (obj.first_name[:1] + obj.last_name[:1]).upper())

    @admin.action(description='Publish selected (appears on website)')
    def publish_players(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Unpublish selected (hide from website)')
    def unpublish_players(self, request, queryset):
        queryset.update(is_published=False)


# ── Coaching staff (Phase 4: admin-settable technical team) ─────────────

class CoachAdminForm(forms.ModelForm):
    """Friendly validation for coach photo uploads.

    The actual re-encode (EXIF/GPS strip, extension fix, bomb cap) is
    enforced by CoachPhotoStorage on every save path; this form adds
    the admin-facing error messages so the office gets a plain-language
    rejection instead of a traceback.
    """

    class Meta:
        model = Coach
        fields = '__all__'

    def clean_photo(self):
        f = self.cleaned_data.get('photo')
        if not f or isinstance(f, str):
            # no new upload (kept existing value / cleared)
            return f
        if f.size > 8 * 1024 * 1024:
            raise forms.ValidationError('Photo is larger than 8 MB — please resize it first.')
        import io
        from pathlib import Path as _Path
        from PIL import Image
        ext = _Path(f.name).suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            raise forms.ValidationError('Photos must be JPG, PNG or WebP.')
        raw = f.read()
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw))
            if (img.width or 0) * (img.height or 0) > 40_000_000:
                raise forms.ValidationError('That image is too large to process — please resize it first.')
            img.load()
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError('That file is not a readable image — it may be damaged or not really a photo.')
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            raise forms.ValidationError('Photos must be JPG, PNG or WebP.')
        return f


@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    form = CoachAdminForm
    list_display = ('thumb', 'name', 'role', 'squad', 'is_published', 'sort')
    list_filter = ('is_published', 'squad')
    search_fields = ('name', 'role', 'bio')
    list_editable = ('is_published', 'sort')
    list_select_related = ('squad',)
    list_per_page = 50
    actions = ('publish_coaches', 'unpublish_coaches')
    fieldsets = (
        ('Profile', {'fields': ('name', 'role', 'squad', 'bio')}),
        ('Photo & publishing', {'fields': ('photo', 'is_published', 'sort')}),
    )

    @admin.display(description='photo')
    def thumb(self, obj):
        if obj.photo:
            try:
                return format_html(
                    '<img src="{}" style="width:42px;height:42px;border-radius:9px;'
                    'object-fit:cover" alt=""/>', obj.photo.url)
            except ValueError:
                pass
        return format_html(
            '<span style="display:inline-grid;place-items:center;width:42px;height:42px;'
            'border-radius:9px;background:#eef0f3;color:#5c6a7e;font-weight:700;'
            'font-size:11px">{}</span>', (obj.name[:2]).upper())

    @admin.action(description='Publish selected (appears on website)')
    def publish_coaches(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Unpublish selected (hide from website)')
    def unpublish_coaches(self, request, queryset):
        queryset.update(is_published=False)


# ── Féminin gallery (rev 25: real photos, uploaded from the backend) ────

class FemininGalleryAdminForm(forms.ModelForm):
    """Friendly validation for gallery photo uploads.

    The actual re-encode (EXIF/GPS strip, extension fix, bomb cap) is
    enforced by FemininGalleryStorage on every save path; this form adds
    the admin-facing error messages so the office gets a plain-language
    rejection instead of a traceback.
    """

    class Meta:
        model = FemininGalleryPhoto
        fields = '__all__'

    def clean_photo(self):
        f = self.cleaned_data.get('photo')
        if not f or isinstance(f, str):
            # no new upload (kept existing value / cleared)
            return f
        if f.size > 8 * 1024 * 1024:
            raise forms.ValidationError('Photo is larger than 8 MB — please resize it first.')
        import io
        from pathlib import Path as _Path
        from PIL import Image
        ext = _Path(f.name).suffix.lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            raise forms.ValidationError('Photos must be JPG, PNG or WebP.')
        raw = f.read()
        try:
            img = Image.open(io.BytesIO(raw))
            img.verify()
            img = Image.open(io.BytesIO(raw))
            if (img.width or 0) * (img.height or 0) > 40_000_000:
                raise forms.ValidationError('That image is too large to process — please resize it first.')
            img.load()
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError('That file is not a readable image — it may be damaged or not really a photo.')
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            raise forms.ValidationError('Photos must be JPG, PNG or WebP.')
        return f


@admin.register(FemininGalleryPhoto)
class FemininGalleryPhotoAdmin(admin.ModelAdmin):
    """Real photos for the Féminin page's 'On the Pitch' gallery.

    The section ships HIDDEN on the website — it appears the moment at
    least one photo here is published. Until then the Féminin page shows
    no gallery at all (no stock stand-ins for the girls' team)."""
    form = FemininGalleryAdminForm
    list_display = ('thumb', 'caption', 'is_published', 'sort', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('caption', 'alt')
    list_editable = ('is_published', 'sort')
    list_per_page = 50
    actions = ('publish_photos', 'unpublish_photos')
    fieldsets = (
        ('Photo', {'fields': ('photo', 'caption', 'alt')}),
        ('Publishing', {'fields': ('is_published', 'sort')}),
    )

    @admin.display(description='photo')
    def thumb(self, obj):
        if obj.photo:
            try:
                return format_html(
                    '<img src="{}" style="width:42px;height:42px;border-radius:9px;'
                    'object-fit:cover" alt=""/>', obj.photo.url)
            except ValueError:
                pass
        return format_html(
            '<span style="display:inline-grid;place-items:center;width:42px;height:42px;'
            'border-radius:9px;background:#eef0f3;color:#5c6a7e;font-weight:700;'
            'font-size:11px">FG</span>')

    @admin.action(description='Publish selected (gallery appears on website)')
    def publish_photos(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Unpublish selected (gallery hides again)')
    def unpublish_photos(self, request, queryset):
        queryset.update(is_published=False)


# ── Restricted safeguarding store (Phase 1) ─────────────────────────────

class _DSOOnlyAdmin(admin.ModelAdmin):
    """Admin surface that only the explicitly-granted DSO role may see.

    Superusers are intentionally NOT exempt: granting the role is the
    auditable act that authorises access. Reports are read-only here —
    the working surface is the branded DSO desk at /portal/dso/.
    """

    def _dso(self, request):
        return is_dso(request.user)

    def has_view_permission(self, request, obj=None):
        return self._dso(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return self._dso(request)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if self._dso(request) else qs.none()


@admin.register(SafeguardingReport)
class SafeguardingReportAdmin(_DSOOnlyAdmin):
    list_display = ('ref', 'status', 'reporter_preference', 'child_name',
                    'created_at', 'assigned_to')
    list_filter = ('status', 'reporter_preference', 'created_at')
    search_fields = ('ref',)
    readonly_fields = [f.name for f in SafeguardingReport._meta.fields]
    date_hierarchy = 'created_at'
    list_per_page = 50

    def has_export_permission(self, request):  # no CSV export of this store
        return False


@admin.register(SafeguardingAuditEntry)
class SafeguardingAuditEntryAdmin(_DSOOnlyAdmin):
    list_display = ('created_at', 'action', 'report_ref', 'actor_username')
    list_filter = ('action',)
    search_fields = ('report_ref', 'actor_username')
    readonly_fields = [f.name for f in SafeguardingAuditEntry._meta.fields]
    list_per_page = 100
