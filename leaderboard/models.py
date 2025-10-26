from django.db import models
from django.utils.text import slugify
from django.utils import timezone # Import timezone

class Player(models.Model):
    """
    A simple model for a competitor. Not linked to a Django user.
    """
    display_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    avatar = models.ImageField(upload_to='player_avatars/', null=True, blank=True)

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.display_name)
        super().save(*args, **kwargs)

class Game(models.Model):
    """
    Metadata for a game.
    """
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField(null=True, blank=True)
    store_url = models.URLField(max_length=500, blank=True)
    image = models.ImageField(upload_to='game_images/', null=True, blank=True)

    def __str__(self):
        return self.title

class Season(models.Model):
    """
    A container for a period of competition, e.g., "Season 1".
    """
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(
        default=False,
        help_text="Mark this as the current season for the global leaderboard."
    )

    def __str__(self):
        return self.name

class Event(models.Model):
    """
    A specific instance of a competition, e.g., "Week 1: Celeste Speedrun".
    """
    season = models.ForeignKey(
        Season,
        on_delete=models.PROTECT,
        related_name="events"
    )
    game = models.ForeignKey(
        Game,
        on_delete=models.PROTECT,
        related_name="events"
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateTimeField()
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    youtube_video_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="The ID from the YouTube URL (e.g., 'dQw4w9WgXcQ')"
    )
    is_details_public = models.BooleanField(
        default=False,
        help_text="If unchecked, only the event name and date will be public."
    )
    def __str__(self):
        return f"{self.season.name}: {self.name}"
    @property
    def is_in_the_past(self):
        """Helper to check if the event date has passed."""
        return self.date < timezone.now()

class Leaderboard(models.Model):
    """
    A specific leaderboard within an event.
    e.g., "Main", "B-Side", "Bonus"
    """
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="leaderboards"
    )
    title = models.CharField(max_length=100)
    description = models.TextField(
        blank=True,
        help_text="Rules for this specific leaderboard."
    )

    def __str__(self):
        return f"{self.event.name} - {self.title}"

class LeaderboardEntry(models.Model):
    """
    A single player's entry on a single leaderboard.
    This is where you manually assign points.
    """
    leaderboard = models.ForeignKey(
        Leaderboard,
        on_delete=models.CASCADE,
        related_name="entries"
    )
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name="entries"
    )
    points = models.PositiveIntegerField(
        default=0,
        help_text="Points awarded for this leaderboard (e.g., 10 for 1st, 9 for 2nd...)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Store raw result here (e.g., 'Time: 1:23.45', 'Score: 500,000')"
    )

    class Meta:
        ordering = ['-points']
        unique_together = [
            ('leaderboard', 'player') # Player can only appear once per leaderboard
        ]
        verbose_name_plural = "Leaderboard Entries"

    def __str__(self):
        return f"{self.player.display_name}: {self.points} pts on {self.leaderboard.title}"