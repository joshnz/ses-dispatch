import asyncio
import json
import time

from django.http import StreamingHttpResponse

_last_change = time.time()


def notify_dispatch_change():
    """Called by any dispatch action to signal that state has changed."""
    global _last_change
    _last_change = time.time()


async def sse_stream(request):
    """Server-Sent Events endpoint for real-time updates."""
    async def event_generator():
        last_check = time.time()
        while True:
            if _last_change > last_check:
                last_check = time.time()
                yield f"event: dispatch-update\ndata: {json.dumps({'ts': last_check})}\n\n"
            await asyncio.sleep(2)

    response = StreamingHttpResponse(
        event_generator(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
