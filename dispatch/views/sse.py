import json
import time

from django.http import JsonResponse

_last_change = time.time()


def notify_dispatch_change():
    """Called by any dispatch action to signal that state has changed."""
    global _last_change
    _last_change = time.time()


def sse_poll(request):
    """Lightweight polling endpoint. Returns the last change timestamp."""
    return JsonResponse({"ts": _last_change})
