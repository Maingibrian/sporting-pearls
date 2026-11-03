from django.urls import path

from . import views

urlpatterns = [
    path('forms/<slug:slug>/', views.submit_form, name='form-submit'),
    path('fixtures/', views.fixtures_list, name='fixtures-list'),
    path('results/', views.results_list, name='results-list'),
    path('gallery/feminin/', views.feminin_gallery, name='feminin-gallery'),
    path('players/', views.players_roster, name='players-roster'),
    path('players/<slug:ref>/', views.player_public, name='player-public'),
    path('coaches/', views.coaches_list, name='coaches-list'),
    path('health/', views.health, name='health'),
]
