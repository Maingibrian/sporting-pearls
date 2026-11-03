from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

from submissions import views
from submissions import portal, portal_desk, portal_dso, portal_auth, portal_qr
from parents import views as parents_views

handler404 = 'submissions.portal_auth.branded_404'
handler500 = 'submissions.portal_auth.branded_500'




urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('submissions.urls')),
    # The branded Management Portal — one login, zero Django chrome.
    path('portal/', portal.portal_home, name='portal-home'),
    path('portal/login/', portal.portal_login, name='portal-login'),
    path('portal/logout/', portal.portal_logout, name='portal-logout'),
    # Phase 2 — staff password reset (no account enumeration).
    path('portal/reset/', portal_auth.staff_reset_request, name='portal-reset'),
    path('portal/reset/<str:uidb64>/<str:token>/', portal_auth.staff_reset_confirm,
         name='portal-reset-confirm'),
    # Phase 5 — externalised dashboard script (staff-only, allow-listed).
    path('portal/assets/<str:name>', portal.portal_asset, name='portal-asset'),
    # Phase 7 — player QR code cards (public profile target is
    # site/player.html; generation lives in portal_qr.py).
    path('portal/qr/', portal_qr.qr_all, name='qr-all'),
    path('portal/qr/<str:ref>/', portal_qr.qr_one, name='qr-one'),
    path('portal/parents/qr/<str:ref>/', portal_qr.parents_qr, name='parents-qr'),
    path('portal/players/add/', portal.player_add, name='portal-player-add'),
    path('portal/players/<int:pid>/toggle/', portal.player_toggle, name='portal-player-toggle'),
    path('portal/players/<int:pid>/delete/', portal.player_delete, name='portal-player-delete'),
    path('portal/players/<int:pid>/edit/', portal.player_edit, name='portal-player-edit'),
    path('portal/players/<int:pid>/photo/', portal.player_photo, name='portal-player-photo'),
    path('portal/submissions/<str:ref>/status/', portal.submission_status, name='portal-sub-status'),
    path('portal/submissions/<str:ref>/invite/', portal.submission_invite, name='portal-sub-invite'),
    path('portal/fixtures/<int:fid>/toggle/', portal.fixture_toggle, name='portal-fixture-toggle'),
    # The branded Parent Portal — guardian accounts opened by invitation.
    path('portal/parents/', parents_views.parents_home, name='parents-home'),
    path('portal/parents/login/', parents_views.parents_login, name='parents-login'),
    path('portal/parents/logout/', parents_views.parents_logout, name='parents-logout'),
    # Phase 2 — parent password reset (no account enumeration).
    path('portal/parents/reset/', portal_auth.parents_reset_request,
         name='parents-reset'),
    path('portal/parents/reset/<str:uidb64>/<str:token>/',
         portal_auth.parents_reset_confirm, name='parents-reset-confirm'),
    path('portal/parents/activate/<str:token>/', parents_views.parents_activate,
         name='parents-activate'),
    # Cycle P2 — dashboard sections.
    path('portal/parents/announcements/', parents_views.parents_announcements,
         name='parents-announcements'),
    path('portal/parents/announcements/<int:aid>/', parents_views.parents_announcement_detail,
         name='parents-announcement'),
    path('portal/parents/child/<int:pid>/', parents_views.parents_child,
         name='parents-child'),
    path('portal/parents/account/', parents_views.parents_account,
         name='parents-account'),
    # Cycle P3 — the welfare desk (parent side).
    path('portal/parents/complaints/', parents_views.parents_complaints,
         name='parents-complaints'),
    path('portal/parents/complaints/<int:cid>/', parents_views.parents_complaint_detail,
         name='parents-complaint'),
    # Cycle P3 — the staff desk (composer + welfare inbox).
    path('portal/desk/announcements/', portal_desk.staff_announcements,
         name='desk-announcements'),
    path('portal/desk/announcements/<int:aid>/toggle/', portal_desk.staff_announcement_toggle,
         name='desk-ann-toggle'),
    path('portal/desk/complaints/', portal_desk.staff_complaints,
         name='desk-complaints'),
    path('portal/desk/complaints/<int:cid>/', portal_desk.staff_complaint_detail,
         name='desk-complaint'),
    # Phase 1 — the restricted DSO desk (safeguarding reports + audit log).
    path('portal/dso/', portal_dso.dso_reports, name='dso-reports'),
    path('portal/dso/r/<str:ref>/', portal_dso.dso_report_detail, name='dso-report'),
    path('portal/dso/audit/', portal_dso.dso_audit, name='dso-audit'),
    # Player photos uploaded from the dashboard. Phase 5 (R17): served
    # through the authenticated gate in portal.media_serve — published
    # players' photos stay public (squad pages), everything else needs a
    # staff session or the owning guardian.
    re_path(r'^media/(?P<path>.*)$', portal.media_serve, name='media-gate'),
    # Health probes: liveness + database readiness (Phase 5, R20). Both
    # paths answer the same JSON — '' keeps old monitors working.
    path('', views.healthz, name='health'),
    path('healthz/', views.healthz, name='healthz'),
]
