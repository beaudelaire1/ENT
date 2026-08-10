from django.db import models
from django.conf import settings


class UserProfile(models.Model):
    """Optional user profile for storing additional metadata.

    This profile extends Django's built‑in user model via a one‑to‑one
    relationship. Additional fields (e.g., biography, organization) can be
    added later without modifying the core User model. Having this app in
    place now paves the way for future user‑centric features.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    organisation = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f"Profil de {self.user.username}"