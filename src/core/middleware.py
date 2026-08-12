from __future__ import annotations

import re
import uuid
from urllib.parse import urlparse

from django.conf import settings

REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class RequestIdMiddleware:
    """Donne un identifiant partageable à chaque réponse et aux journaux de requête."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "")
        request.request_id = supplied if REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class SecurityHeadersMiddleware:
    """Politique locale : aucun script tiers, aucun cadre, aucun objet embarqué."""

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def external_sources():
        sources = list(getattr(settings, "CSP_EXTERNAL_MEDIA_SOURCES", []))
        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", "")
        if endpoint:
            parsed = urlparse(endpoint)
            if parsed.scheme and parsed.netloc:
                sources.append(f"{parsed.scheme}://{parsed.netloc}")
        return " ".join(dict.fromkeys(sources))

    def __call__(self, request):
        response = self.get_response(request)
        media = self.external_sources()
        response["Content-Security-Policy"] = "; ".join(
            [
                "default-src 'self'",
                "script-src 'self'",
                # Les palettes et barres de progression sont encore calculées en style
                # inline ; les scripts, eux, restent strictement locaux.
                "style-src 'self' 'unsafe-inline'",
                f"img-src 'self' data: blob: {media}".strip(),
                f"media-src 'self' blob: {media}".strip(),
                "connect-src 'self'",
                "font-src 'self'",
                "object-src 'none'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
            ]
        )
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        return response
