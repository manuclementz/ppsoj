from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q, Prefetch, F, Window
from django.db.models.functions import Rank
from .models import Player, Season, Event, Leaderboard, LeaderboardEntry


def event_detail(request, event_id):
    """
    Affiche les détails d'un seul événement.
    """
    
    event = get_object_or_404(
        Event.objects.select_related('game').prefetch_related(
            Prefetch(
                'leaderboards', 
                queryset=Leaderboard.objects.prefetch_related( 
                    Prefetch(
                        'entries', 
                        queryset=LeaderboardEntry.objects.annotate(
                            rank=Window(
                                expression=Rank(),
                                
                                partition_by=F('leaderboard_id'), 
                                
                                order_by=F('points').desc()
                            )
                        ).select_related('player'), 
                        
                        to_attr='ranked_entries' 
                    )
                )
            )
        ),
        id=event_id
    )
    
    context = {
        'event': event,
        'all_seasons': Season.objects.all().order_by('-start_date'),
    }
    return render(request, 'leaderboard/event_detail.html', context)


def get_season(season_id=None):
    """Helper function to get the season we care about."""
    if season_id:
        # Get a specific season by its ID
        return get_object_or_404(Season, id=season_id)
    
    try:
        # Or, get the one marked 'is_active'
        return Season.objects.get(is_active=True)
    except Season.DoesNotExist:
        # Fallback if none are active
        return Season.objects.all().order_by('-start_date').first()

def season_leaderboard(request, season_id=None):
    # ... (get_season est inchangé) ...
    current_season = get_season(season_id)
    leaderboard_data = Player.objects.none()
    all_events = Event.objects.none()

    if current_season:
        # 1. MODIFICATION : Calculer le classement global AVEC Rank()
        leaderboard_data = Player.objects.annotate(
            total_points=Sum(
                'entries__points',
                filter=Q(entries__leaderboard__event__season=current_season)
            )
        ).filter(total_points__gt=0).annotate(
            # AJOUT DE CETTE LIGNE :
            # Calcule le rang en se basant sur total_points
            rank=Window(
                expression=Rank(),
                order_by=F('total_points').desc()
            )
        ).order_by('rank', 'display_name') # Trier par le nouveau rang

        # 2. Trier les événements (inchangé)
        all_events = Event.objects.filter(
            season=current_season
        ).order_by('is_details_public', 'date')

    context = {
        'season': current_season,
        'leaderboard': leaderboard_data,
        'all_events': all_events, 
        'all_seasons': Season.objects.all().order_by('-start_date'),
    }
    return render(request, 'leaderboard/season_leaderboard.html', context)

def event_list(request, season_id=None):
    """
    Displays a list of events.
    Shows the active season's events by default, or a specific one.
    """
    current_season = get_season(season_id)
    event_list_data = Event.objects.none()

    if current_season:
        event_list_data = Event.objects.filter(
            season=current_season
        ).order_by('-date')

    context = {
        'season': current_season,
        'event_list': event_list_data,
        # Pass all seasons to the template for the dropdown
        'all_seasons': Season.objects.all().order_by('-start_date'),
    }
    return render(request, 'leaderboard/event_list.html', context)

def player_detail(request, player_slug):
    """
    Displays a profile page for a single player.
    """
    player = get_object_or_404(Player, slug=player_slug)
    
    # Get the current season for stats
    current_season = get_season()
    
    # Get this player's rank and score for the current season
    # We re-use the same logic from the main leaderboard...
    season_stats = Player.objects.annotate(
        total_points=Sum(
            'entries__points',
            filter=Q(entries__leaderboard__event__season=current_season)
        )
    ).filter(total_points__gt=0).annotate(
        # ...and add a Rank calculation
        rank=Window(
            expression=Rank(),
            order_by=F('total_points').desc()
        )
    ).filter(id=player.id).first() # Get just this player's stats
    
    # Get all of the player's entries from all seasons
    participation_history = LeaderboardEntry.objects.filter(
        player=player
    ).select_related(
        'leaderboard__event__season'
    ).order_by('-leaderboard__event__date')

    context = {
        'player': player,
        'season': current_season,
        'season_stats': season_stats, # Will be None if player has no points
        'participation_history': participation_history,
        'all_seasons': Season.objects.all().order_by('-start_date'),
    }
    return render(request, 'leaderboard/player_detail.html', context)