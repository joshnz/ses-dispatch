"""
Role-based redirect middleware.
Redirects crew-role users to the crew screen and prevents them from
accessing ICP-only views.
"""
from django.shortcuts import redirect

CREW_ALLOWED_PATHS = [
    "/crew-screen/",
    "/htmx/crew-screen-content/",
    "/action/on-scene/",
    "/action/complete/",
    "/events/",
    "/accounts/",
    "/static/",
    "/media/",
]


class RoleRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.user.is_authenticated
                and request.user.groups.filter(name="Crew").exists()):
            path = request.path
            if not any(path.startswith(allowed) for allowed in CREW_ALLOWED_PATHS):
                return redirect("crew_screen")

        return self.get_response(request)
