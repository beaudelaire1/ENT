from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from .models import UserProfile


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone_name = settings.TIME_ZONE
        if request.user.is_authenticated:
            try:
                timezone_name = request.user.profile.timezone
            except ObjectDoesNotExist:
                timezone_name = UserProfile.objects.create(user=request.user).timezone
        try:
            timezone.activate(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            timezone.activate(ZoneInfo(settings.TIME_ZONE))
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
