from django.db import models
from django.utils.text import slugify
from django.utils import timezone
import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile

def _process_image(image_field, max_dims=None):
    img = Image.open(image_field)

    if max_dims:
        img.thumbnail(max_dims, Image.Resampling.LANCZOS)

    output_buffer = BytesIO()
    img.save(output_buffer, format='WEBP', quality=85)
    output_buffer.seek(0)

    file_name = os.path.splitext(image_field.name)[0] + '.webp'

    return file_name, ContentFile(output_buffer.read())

class Player(models.Model):
    display_name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    avatar = models.ImageField(upload_to='player_avatars/', null=True, blank=True)

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.display_name)
        
        old_avatar = None
        if self.pk:
            try:
                old_avatar = Player.objects.get(pk=self.pk).avatar
            except Player.DoesNotExist:
                pass
        
        if self.avatar and self.avatar != old_avatar:
            file_name, content = _process_image(self.avatar, max_dims=(250, 250))
            self.avatar.save(file_name, content, save=False)

        super().save(*args, **kwargs)

class Game(models.Model):
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField(null=True, blank=True)
    store_url = models.URLField(max_length=500, blank=True)
    image = models.ImageField(upload_to='game_images/', null=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        old_image = None
        if self.pk:
            try:
                old_image = Game.objects.get(pk=self.pk).image
            except Game.DoesNotExist:
                pass
        
        if self.image and self.image != old_image:
            file_name, content = _process_image(self.image, max_dims=None)
            self.image.save(file_name, content, save=False)
            
        super().save(*args, **kwargs)

class Season(models.Model):
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
        return self.date < timezone.now()

    def save(self, *args, **kwargs):
        old_image = None
        if self.pk:
            try:
                old_image = Event.objects.get(pk=self.pk).image
            except Event.DoesNotExist:
                pass
        
        if self.image and self.image != old_image:
            file_name, content = _process_image(self.image, max_dims=None)
            self.image.save(file_name, content, save=False)
            
        super().save(*args, **kwargs)

class Leaderboard(models.Model):
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
            ('leaderboard', 'player')
        ]
        verbose_name_plural = "Leaderboard Entries"

    def __str__(self):
        return f"{self.player.display_name}: {self.points} pts on {self.leaderboard.title}"