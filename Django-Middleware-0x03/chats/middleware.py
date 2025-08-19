# chats/middleware.py
from datetime import datetime, timedelta
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger("request_logger")


def _get_client_ip(request):
    """Best-effort client IP extraction."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


class RequestLoggingMiddleware:
    """
    Logs every request: timestamp, user (or 'anon'), and path.
    Format: "YYYY-mm-dd HH:MM:SS - User: <user> - Path: <path>"
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "anonymous"
        ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"{ts} - User: {user} - Path: {request.path}")
        return self.get_response(request)


class RestrictAccessByTimeMiddleware:
    """
    Deny access outside business hours.
    Spec says: block access outside 6PM–9PM? (ambiguous)
    We'll implement a common rule: allow 06:00–21:00; block otherwise.
    Modify START_HOUR/END_HOUR as needed.
    """
    START_HOUR = 6   # 06:00 inclusive
    END_HOUR = 21    # 21:00 exclusive

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        now = timezone.localtime()
        hour = now.hour
        allowed = self.START_HOUR <= hour < self.END_HOUR
        if not allowed:
            return HttpResponseForbidden("Chat is closed. Please come back during allowed hours.")
        return self.get_response(request)


class OffensiveLanguageMiddleware:
    """
    (Task text mixes 'offensive language' and 'rate limit'.)
    Implement a per-IP rate limit for POSTs to /chats*:
      - 5 messages per 60 seconds per IP.
    Uses Django cache (Local-memory cache works out of the box).
    """
    WINDOW_SECONDS = 60
    MAX_MESSAGES = 5
    SCOPE_PREFIX = "chat_rate_"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only enforce on POSTs to chats endpoints
        if request.method == "POST" and request.path.startswith("/chats"):
            ip = _get_client_ip(request)
            key = f"{self.SCOPE_PREFIX}{ip}"
            bucket = cache.get(key, {"count": 0, "reset_at": timezone.now() + timedelta(seconds=self.WINDOW_SECONDS)})

            # Reset window if expired
            if timezone.now() >= bucket["reset_at"]:
                bucket = {"count": 0, "reset_at": timezone.now() + timedelta(seconds=self.WINDOW_SECONDS)}

            bucket["count"] += 1
            if bucket["count"] > self.MAX_MESSAGES:
                cache.set(key, bucket, self.WINDOW_SECONDS)  # maintain window
                return HttpResponseForbidden("Rate limit exceeded: max 5 messages per minute.")
            cache.set(key, bucket, self.WINDOW_SECONDS)
        return self.get_response(request)


class RolepermissionMiddleware:
    """
    Enforce admin/moderator role for protected paths.
    Protect paths under /chats/admin or /chats/moderate by default.
    """
    PROTECTED_PREFIXES = ("/chats/admin", "/chats/moderate")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self.PROTECTED_PREFIXES):
            user = getattr(request, "user", None)
            is_allowed = (
                user
                and user.is_authenticated
                and (user.is_superuser or user.groups.filter(name__in=["admin", "moderator"]).exists())
            )
            if not is_allowed:
                return HttpResponseForbidden("Forbidden: admin/moderator role required.")
        return self.get_response(request)
