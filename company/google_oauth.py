from __future__ import annotations

import os
if os.getenv("DEBUG", "True").lower() == "true":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from django.conf import settings
from google_auth_oauthlib.flow import Flow


def build_google_flow():
    """Build and configure Google OAuth2 flow with validation."""
    # Validate credentials are configured
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise ValueError(
            "GOOGLE_OAUTH_CLIENT_ID is not configured. "
            "Add it to your .env file (get from Google Cloud Console)."
        )
    if not settings.GOOGLE_OAUTH_CLIENT_SECRET:
        raise ValueError(
            "GOOGLE_OAUTH_CLIENT_SECRET is not configured. "
            "Add it to your .env file (get from Google Cloud Console)."
        )
    
    scopes = getattr(settings, "GOOGLE_CALENDAR_SCOPES", [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/userinfo.email",
    ])
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
            }
        },
        scopes=scopes,
    )
    flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
    return flow