from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.conf import settings
import re

register = template.Library()

def simple_strip(text):
    """A very simple function to strip markdown-like characters for a description."""
    text = re.sub(r'[#*]', '', text) # Remove markdown emphasis
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text) # Keep text from links
    text = re.sub(r'\s+', ' ', text).strip() # Normalize whitespace
    return text

def generate_cache_key(request, context):
    """Generate a unique cache key based on the current URL."""
    # Since content can change based on many models, we'll
    # rely on a simple URL key and the cache timeout.
    return f'og_meta_tags:{request.build_absolute_uri()}'

def generate_meta_tags(request, context):
    """Generate OpenGraph and Twitter Card meta tags based on the current page context"""
    page_type = context.get('og_type', 'website')
    meta_tags = []
    
    # Site name (Updated Default)
    site_name = getattr(settings, 'OG_SITE_NAME', 'Pôle Posisoj')
    meta_tags.append(f'<meta property="og:site_name" content="{escape(site_name)}">')
    
    # Basic tags
    meta_tags.extend([
        f'<meta property="og:type" content="{page_type}">',
        f'<meta property="og:url" content="{request.build_absolute_uri()}">'
    ])
    
    # Title (Adapted for new context)
    title = site_name # Default
    if 'player' in context:
        title = f"Profil de {context['player'].display_name} | {site_name}"
    elif 'event' in context:
        title = f"{context['event'].name} | {site_name}"
    elif 'season' in context:
        title = f"Classement - {context['season'].name} | {site_name}"
        
    meta_tags.extend([
        f'<meta property="og:title" content="{escape(title)}">',
        f'<meta name="twitter:title" content="{escape(title)}">'
    ])
    
    # Description (Adapted for new context)
    description = "Classements des compétitions Pôle Posisoj." # Default
    
    if 'player' in context:
        description = f"Consultez les stats et l'historique des participations de {context['player'].display_name}."
    elif 'event' in context:
        if context['event'].description:
            desc = simple_strip(context['event'].description)
            description = desc[:160] + '...' if len(desc) > 160 else desc
        else:
            description = f"Consultez les classements pour l'événement {context['event'].name}."
    elif 'season' in context:
        description = f"Classement global et événements pour la saison {context['season'].name}."
        
    meta_tags.extend([
        f'<meta property="og:description" content="{escape(description)}">',
        f'<meta name="twitter:description" content="{escape(description)}">'
    ])
    
    # Twitter specific tags
    twitter_handle = getattr(settings, 'TWITTER_HANDLE', '') # Set this in settings.py
    if twitter_handle:
        meta_tags.append(f'<meta name="twitter:site" content="@{escape(twitter_handle)}">')
    
    # Use 'summary' card since we have no images
    meta_tags.append('<meta name="twitter:card" content="summary">') 
    
    # All image logic has been removed as requested.
    
    return '\n'.join(meta_tags)

@register.simple_tag(takes_context=True)
def og_meta_tags(context):
    """
    Template tag that returns cached OpenGraph and Twitter Card meta tags.
    Cache duration is set by OG_META_CACHE_TIMEOUT in settings (defaults to 1 hour).
    """
    request = context['request']
    
    # Skip caching in debug mode if configured
    if getattr(settings, 'OG_META_SKIP_CACHE_IN_DEBUG', False) and settings.DEBUG:
        return mark_safe(generate_meta_tags(request, context))
    
    cache_key = generate_cache_key(request, context)
    cached_tags = cache.get(cache_key)
    
    if cached_tags is None:
        cached_tags = generate_meta_tags(request, context)
        timeout = getattr(settings, 'OG_META_CACHE_TIMEOUT', 3600)  # Default 1 hour
        cache.set(cache_key, cached_tags, timeout)
    
    return mark_safe(cached_tags)