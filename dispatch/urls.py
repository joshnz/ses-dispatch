from django.urls import path
from .views import dashboard, crew_screen, dispatch_actions, sse

urlpatterns = [
    # Main pages
    path("", dashboard.dashboard, name="dashboard"),
    path("jobs/", dashboard.job_queue, name="job_queue"),
    path("crews/", dashboard.crew_status, name="crew_status"),
    path("recommendations/", dashboard.recommendations, name="recommendations"),
    path("settings/", dashboard.dispatch_settings, name="settings"),
    path("crew-screen/", crew_screen.crew_screen, name="crew_screen"),

    # HTMX partials
    path("htmx/metrics/", dashboard.htmx_metrics),
    path("htmx/crew-screen-content/<int:pk>/", crew_screen.htmx_crew_screen_content),
    path("htmx/map-data/", dashboard.htmx_map_data),
    path("htmx/job-detail/<int:pk>/", dashboard.htmx_job_detail_modal),
    path("htmx/crew-queue/<int:crew_id>/", dispatch_actions.htmx_crew_queue),

    # Actions (POST)
    path("action/dispatch/", dispatch_actions.dispatch_crew, name="dispatch_crew"),
    path("action/complete/<int:job_id>/", dispatch_actions.complete_job),
    path("action/cancel/<int:job_id>/", dispatch_actions.cancel_job),
    path("action/on-scene/<int:crew_id>/", dispatch_actions.on_scene),
    path("action/return-to-base/<int:crew_id>/", dispatch_actions.return_to_base),
    path("action/toggle-crew/<int:crew_id>/", dispatch_actions.toggle_crew),
    path("action/send-upload-link/<int:job_id>/", dispatch_actions.send_upload_link),
    path("action/queue/<int:crew_id>/add/", dispatch_actions.add_to_queue),
    path("action/queue/<int:crew_id>/<int:job_id>/", dispatch_actions.remove_from_queue_view),
    path("action/reorder-queue/<int:crew_id>/", dispatch_actions.reorder_queue_view),

    # SSE
    path("events/", sse.sse_stream, name="sse_stream"),
]
