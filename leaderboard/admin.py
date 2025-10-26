from django.contrib import admin
from django.utils.html import format_html
from .models import Player, Game, Season, Event, Leaderboard, LeaderboardEntry

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    """
    Admin for Players.
    """
    list_display = ('get_avatar', 'display_name', 'slug')
    
    search_fields = ('display_name',)
    prepopulated_fields = {'slug': ('display_name',)}

    @admin.display(description='Avatar')
    def get_avatar(self, obj):
        if obj.avatar:
            # Display a small circular preview
            return format_html(
                '<img src="{}" width="40" height="40" style="object-fit: cover; border-radius: 50%;" />',
                obj.avatar.url
            )
        return "No Avatar"

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    """
    Admin for Games.
    """
    list_display = ('title', 'year')
    search_fields = ('title',)

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    """
    Admin for Seasons. You can easily see which one is active.
    """
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

# --- Inlines for easy nested data entry ---

class LeaderboardEntryInline(admin.TabularInline):
    """
    This inline allows you to add player entries *directly* inside
    the Leaderboard admin page.
    
    'TabularInline' shows it as a compact table.
    """
    model = LeaderboardEntry
    # Use autocomplete for players, which is better than a giant dropdown
    autocomplete_fields = ('player',)
    # Show 10 empty slots by default
    extra = 10 
    # Order by points by default so you can see the rank
    ordering = ('-points',)

class LeaderboardInline(admin.StackedInline):
    """
    This inline allows you to add Leaderboards *directly* inside
    the Event admin page.
    
    'StackedInline' gives each leaderboard its own block.
    """
    model = Leaderboard
    # Show one empty slot by default
    extra = 1
    # **This is the nesting part:**
    # We put the Entry inline *inside* the Leaderboard inline
    inlines = [LeaderboardEntryInline]

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """
    This is the main admin page for managing a competition event.
    """
    list_display = ('name', 'season', 'game', 'date', 'is_details_public')
    list_filter = ('season', 'game')
    search_fields = ('name',)
    # Autocomplete fields are great for linked models
    autocomplete_fields = ('game', 'season')
    fieldsets = (
        (None, {
            'fields': ('season', 'game', 'name', 'date', 'is_details_public')
        }),
        ('Event Details (Public)', {
            'classes': ('collapse',),
            'fields': ('description', 'image', 'youtube_video_id')
        }),
    )
    # **This is where the magic happens:**
    # We nest the Leaderboard inline (which contains the Entry inline)
    # right into the Event page.
    inlines = [LeaderboardInline]

@admin.register(Leaderboard)
class LeaderboardAdmin(admin.ModelAdmin):
    """
    This provides a standalone admin page for leaderboards.
    
    It's useful if you want to edit a leaderboard without
    going through its Event page first.
    """
    list_display = ('title', 'event')
    list_filter = ('event__season', 'event__game')
    search_fields = ('title', 'event__name')
    # We also add the entry inline here for editing
    inlines = [LeaderboardEntryInline]
