import json
import time

from django.http import JsonResponse

_last_change = time.time()
_photo_notifications = []


def notify_dispatch_change():
    """Called by any dispatch action to signal that state has changed."""
    global _last_change
    _last_change = time.time()


def notify_photo_upload(sierra_number, photo_count):
    """Called when a photo is uploaded to trigger a toast notification."""
    global _last_change
    _last_change = time.time()
    _photo_notifications.append({
        "sierra": sierra_number,
        "count": photo_count,
        "ts": _last_change,
    })
    # Keep only the last 20 notifications
    if len(_photo_notifications) > 20:
        _photo_notifications.pop(0)


def sse_poll(request):
    """Lightweight polling endpoint. Returns the last change timestamp."""
    since = float(request.GET.get("since", 0))
    new_photos = [n for n in _photo_notifications if n["ts"] > since]
    # Remove delivered notifications to prevent duplicate toasts
    if new_photos:
        cutoff = new_photos[-1]["ts"]
        _photo_notifications[:] = [n for n in _photo_notifications if n["ts"] > cutoff]
    return JsonResponse({"ts": _last_change, "photo_uploads": new_photos})
