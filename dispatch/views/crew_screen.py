from django.shortcuts import render, get_object_or_404
from dispatch.models import Crew


def crew_screen(request):
    crew_id = request.GET.get("crew")
    crews = Crew.objects.all()
    crew = None

    if crew_id:
        crew = get_object_or_404(Crew, pk=crew_id)

    return render(request, "dispatch/crew_screen.html", {
        "crews": crews,
        "crew": crew,
    })


def htmx_crew_screen_content(request, pk):
    crew = get_object_or_404(Crew, pk=pk)
    return render(request, "dispatch/partials/crew_screen_content.html", {
        "crew": crew,
    })
