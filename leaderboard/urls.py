from django.urls import path
from . import views

app_name = 'leaderboard' 

urlpatterns = [
    # Shows active season leaderboard (homepage)
    path('', views.season_leaderboard, name='season_leaderboard'),
    # Shows a specific season's leaderboard
    path('season/<int:season_id>/', views.season_leaderboard, name='season_leaderboard_archived'),
    
    # Shows active season events
    path('events/', views.event_list, name='event_list'),
    # Shows a specific season's events
    path('events/season/<int:season_id>/', views.event_list, name='event_list_archived'),
    
    # e.g., /event/5/
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    
    # --- NEW URL FOR PLAYER DETAILS ---
    path('player/<slug:player_slug>/', views.player_detail, name='player_detail'),
    # ----------------------------------
]