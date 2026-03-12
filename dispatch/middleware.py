"""Request profiling middleware for performance debugging."""
import logging
import time
import traceback

from django.conf import settings
from django.db import connection, reset_queries

logger = logging.getLogger("dispatch.profiler")


class RequestProfilingMiddleware:
    """Logs request duration and query count for every request.

    When DEBUG=True, also logs individual slow SQL queries.
    When DEBUG=False, still logs request timing via a lightweight
    query counter callback.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()

        # Force query logging for this request if DEBUG is True
        if settings.DEBUG:
            reset_queries()
            force_debug = False
        else:
            # Temporarily enable query logging
            force_debug = not connection.force_debug_cursor
            connection.force_debug_cursor = True
            reset_queries()

        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(
                "EXCEPTION: %s %s after %.0fms\n%s",
                request.method, request.path, duration_ms,
                traceback.format_exc(),
            )
            raise
        finally:
            if force_debug:
                connection.force_debug_cursor = False

        duration_ms = (time.monotonic() - start) * 1000
        query_count = len(connection.queries)
        query_time_ms = sum(
            float(q.get("time", 0)) for q in connection.queries
        ) * 1000

        path = request.path
        method = request.method
        status = response.status_code

        msg = (
            f"{method} {path} -> {status} | "
            f"{duration_ms:.0f}ms total | "
            f"{query_count} queries ({query_time_ms:.0f}ms SQL)"
        )

        if duration_ms > 1000:
            logger.warning("SLOW: %s", msg)
            for q in connection.queries:
                qt = float(q.get("time", 0))
                if qt > 0.05:
                    logger.warning(
                        "  Slow query (%.0fms): %s",
                        qt * 1000, q.get("sql", "")[:300],
                    )
        elif duration_ms > 500:
            logger.warning(msg)
        elif not path.startswith("/static"):
            logger.info(msg)

        return response
