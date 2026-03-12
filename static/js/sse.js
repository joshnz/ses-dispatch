/* SSE (Server-Sent Events) client for real-time dispatch updates */
(function() {
    const evtSource = new EventSource("/events/");

    evtSource.addEventListener("dispatch-update", function(e) {
        // Trigger HTMX event so all listening elements refresh
        htmx.trigger(document.body, "dispatch-changed");
    });

    evtSource.onerror = function() {
        console.warn("SSE connection lost. Reconnecting...");
    };
})();
