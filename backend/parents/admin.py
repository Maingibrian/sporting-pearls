"""Admin surfaces for parent accounts.

Guardian / invite management lives here as a safety net — the intended
day-to-day route is the branded portal's "Approve & invite guardian" button
on a submission. The invite admin can re-send a link (fresh 72 h window).
"""
from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from submissions.models import FormSubmission

from .models import (Announcement, Complaint, ComplaintReply, Guardian,
                     GuardianPlayer, ParentInvite)
from . import services


class GuardianPlayerInline(admin.TabularInline):
    model = GuardianPlayer
    extra = 0
    autocomplete_fields = ('player',)


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'phone', 'relation', 'is_active',
                    'children_count', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('relation', 'is_active')
    search_fields = ('full_name', 'phone', 'user__username')
    inlines = [GuardianPlayerInline]

    @admin.display(description='children')
    def children_count(self, obj):
        return obj.links.count()


@admin.register(ParentInvite)
class ParentInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'guardian_name', 'child', 'created_at',
                    'expires_at', 'accepted_at', 'email_status')
    list_filter = ('email_status', 'relation')
    search_fields = ('email', 'guardian_name')
    readonly_fields = ('token', 'created_at', 'expires_at', 'accepted_at',
                       'email_status', 'email_error', 'invite_link')
    actions = ('resend_invite',)

    @admin.display(description='child')
    def child(self, obj):
        return str(obj.player) if obj.player else '—'

    @admin.display(description='activation link (copy it)')
    def invite_link(self, obj):
        if obj.is_accepted:
            return format_html('<span style="color:#8a94a6">already activated</span>')
        return format_html('<code>/portal/parents/activate/{}</code>', obj.token)

    @admin.action(description='Re-send invite email (fresh 72 hours)')
    def resend_invite(self, request, queryset):
        sent, skipped = 0, 0
        for invite in queryset:
            if invite.is_accepted:
                skipped += 1
                continue
            invite.expires_at = timezone.now() + timezone.timedelta(
                hours=services.INVITE_TTL_HOURS)
            self._send_only(request, invite)
            sent += 1
        self.message_user(request, f'Re-sent {sent} invite(s), {skipped} skipped (already activated).')

    def _send_only(self, request, invite):
        url = request.build_absolute_uri(f'/portal/parents/activate/{invite.token}/')
        payload = services.invite_email_payload(
            url, invite.guardian_name,
            f"your child {invite.player.first_name}'s " if invite.player else '')
        payload.update({'from': settings.EMAIL_FROM, 'to': [invite.email]})
        ok, detail = services.resend_send(payload)
        invite.email_status = ('sent' if ok else detail)[:32]
        invite.email_error = '' if ok else detail
        invite.save(update_fields=['email_status', 'email_error'])


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'pinned', 'is_published', 'published_at', 'created_at')
    list_editable = ('pinned', 'is_published')
    filter_horizontal = ('squads',)
    search_fields = ('title', 'body')
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        if obj.is_published and obj.published_at is None:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


class ComplaintReplyInline(admin.TabularInline):
    model = ComplaintReply
    extra = 0
    fields = ('by_staff', 'by_guardian', 'body', 'is_internal', 'created_at')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('by_staff',)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('subject', 'guardian', 'player', 'category', 'status',
                    'assigned_to', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('subject', 'message', 'guardian__full_name')
    inlines = [ComplaintReplyInline]
    actions = ('mark_in_review', 'mark_resolved', 'mark_closed')

    @admin.action(description='Mark as in review')
    def mark_in_review(self, request, queryset):
        queryset.update(status='in_review')

    @admin.action(description='Mark as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')

    @admin.action(description='Mark as closed')
    def mark_closed(self, request, queryset):
        queryset.update(status='closed')


# ── "Approve & invite guardian" action on submissions ───────────────────

@admin.action(description='Approve & invite guardian (sends activation email)')
def approve_and_invite(modeladmin, request, queryset):
    invited, failed, skipped = [], [], 0
    for sub in queryset:
        pf = services.prefill_from_submission(sub)
        if not pf['email']:
            skipped += 1
            continue
        player = services.find_child(pf['child_name'], pf['squad_hint'])
        invite, ok, detail = services.create_and_send_invite(
            guardian_name=pf['guardian_name'] or pf['child_name'] + "'s guardian",
            email=pf['email'], player=player, invited_by=request.user,
            submission=sub, request=request)
        if invite is not None and ok:
            invited.append(sub.ref)
        elif invite is not None:
            failed.append(f'{sub.ref}: {detail}')
        else:
            failed.append(f'{sub.ref}: {detail}')
    msg = f'{len(invited)} guardian invite(s) sent.'
    if skipped:
        msg += f' {skipped} skipped (no email in the answers — invite them from the branded portal).'
    if failed:
        msg += ' Problems: ' + ' · '.join(failed)
    modeladmin.message_user(request, msg)


# Attach the action to the existing submissions admin (defined in
# submissions.admin) without touching that module's logic.
def _register_submission_action():
    admin_obj = admin.site._registry.get(FormSubmission)
    if admin_obj is None:
        return
    if 'approve_and_invite' not in admin_obj.actions:
        admin_obj.actions = tuple(admin_obj.actions) + ('approve_and_invite',)
    setattr(admin_obj, 'approve_and_invite', approve_and_invite)


_register_submission_action()
