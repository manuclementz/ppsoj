from django.shortcuts import render, get_object_or_404
from django.db.models import Sum, Q, Prefetch, F, Window, Count
from django.db.models.functions import Rank
from .models import Player, Season, Event, Leaderboard, LeaderboardEntry

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
    """
    Displays the global leaderboard, stats, and event list for a season.
    """
    current_season = get_season(season_id)
    leaderboard_data = Player.objects.none()
    stats = {} 
    upcoming_events = Event.objects.none()
    past_events = Event.objects.none()

    if current_season:
        # 1. Calculate leaderboard data (unchanged)
        leaderboard_data = Player.objects.annotate(
            total_points=Sum(
                'entries__points',
                filter=Q(entries__leaderboard__event__season=current_season)
            )
        ).filter(
            total_points__gt=0
        ).annotate(
            rank=Window(
                expression=Rank(),
                order_by=F('total_points').desc()
            )
        ).order_by('rank', 'display_name') 

        # 2. --- THIS SECTION IS UPDATED ---
        # Get all events for the season
        all_events_qs = Event.objects.filter(season=current_season)
        
        # Split them into two querysets
        # Upcoming: not public, ordered by date (soonest first)
        upcoming_events = all_events_qs.filter(
            is_details_public=False
        ).order_by('date')
        
        # Past: public, ordered by date (most recent first)
        past_events = all_events_qs.filter(
            is_details_public=True
        ).order_by('-date')
        # --- END OF UPDATE ---

        # 3. Calculate stats
        leaderboard_list = list(leaderboard_data)
        
        stats['total_players'] = len(leaderboard_list)
        stats['total_events'] = all_events_qs.count() # Count all events
        stats['total_points_awarded'] = sum(p.total_points for p in leaderboard_list) or 0
        
        stats['podium_1'] = [p for p in leaderboard_list if p.rank == 1]
        stats['podium_2'] = [p for p in leaderboard_list if p.rank == 2]
        stats['podium_3'] = [p for p in leaderboard_list if p.rank == 3]

    context = {
        'season': current_season,
        'leaderboard': leaderboard_list, 
        'upcoming_events': upcoming_events, # NEW
        'past_events': past_events,       # NEW
        'all_seasons': Season.objects.all().order_by('-start_date'),
        'stats': stats, 
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

def player_detail(request, player_slug):
    """
    Displays a profile page for a single player.
    """
    player = get_object_or_404(Player, slug=player_slug)
    current_season = get_season()
    
 # --- THIS IS THE CORRECTED LOGIC ---

    # 1. Get the player's own total points for the current season.
    # We use filter(id=...).first() to get an annotated object.
    season_stats = Player.objects.filter(id=player.id).annotate(
        total_points=Sum(
            'entries__points',
            filter=Q(entries__leaderboard__event__season=current_season)
        )
    ).first() # Query 1: Get this player's points

    # 2. Check if the player participated and has points (total_points > 0)
    #    We must check for 'None' in case the Sum() returns None.
    player_points = season_stats.total_points or 0
    
    if player_points > 0:
        # 3. If they do, count how many *other* players have a *higher* score.
        #    This is the definition of Rank.
        higher_scores_count = Player.objects.annotate(
            season_points=Sum(
                'entries__points',
                filter=Q(entries__leaderboard__event__season=current_season)
            )
        ).filter(
            season_points__gt=player_points
        ).count() # Query 2: Get count of players with more points
        
        # 4. Their rank is 1 + the number of people above them
        season_stats.rank = higher_scores_count + 1
    else:
        # 5. They have 0 points, so they are unranked.
        season_stats.total_points = 0 # Ensure it's 0, not None
        season_stats.rank = None # Or 'N/A' for the template
    
    # --- END OF CORRECTED LOGIC ---
    
    # 3. Get all-time participation history (unchanged)
    participation_history = LeaderboardEntry.objects.filter(
        player=player
    ).select_related(
        'leaderboard__event__season'
    ).order_by('-leaderboard__event__date')
    
    # 4. Calculate new all-time stats (unchanged)
    all_time_stats = {}
    all_time_stats['participations'] = participation_history.count()
    all_time_stats['total_points'] = participation_history.aggregate(total=Sum('points'))['total'] or 0
    all_time_stats['wins'] = participation_history.filter(points=10).count() # Proxy for wins
    all_time_stats['seasons'] = participation_history.values('leaderboard__event__season').distinct().count()

    context = {
        'player': player,
        'season': current_season,
        'season_stats': season_stats, # This will now have the correct .rank
        'all_time_stats': all_time_stats, 
        'participation_history': participation_history,
        'all_seasons': Season.objects.all().order_by('-start_date'),
    }
    return render(request, 'leaderboard/player_detail.html', context)