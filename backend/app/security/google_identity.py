"""Verify Google OpenID Connect tokens presented by the mobile app."""

from __future__ import annotations

from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token


def verify_google_id_token(token: str, audience: str) -> dict[str, Any]:
    """Return verified Google claims or raise ValueError for an invalid token."""
    claims = google_id_token.verify_oauth2_token(
        token,
        google_requests.Request(),
        audience,
    )
    if claims.get("iss") not in {
        "accounts.google.com",
        "https://accounts.google.com",
    }:
        raise ValueError("Unexpected Google token issuer.")
    if claims.get("email_verified") is not True:
        raise ValueError("The Google account email is not verified.")
    if not claims.get("sub") or not claims.get("email"):
        raise ValueError("The Google token is missing required identity claims.")
    return claims
