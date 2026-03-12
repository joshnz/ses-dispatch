/* Real-time dispatch updates via polling.
   SSE with sync Gunicorn workers holds one thread per connection,
   so we use lightweight polling instead. */
(function() {
    var pollInterval = 5000;
    var lastTs = 0;

    function poll() {
        fetch("/events/poll/")
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.ts > lastTs) {
                    lastTs = data.ts;
                    if (lastTs > 0) {
                        htmx.trigger(document.body, "dispatch-changed");
                    }
                }
            })
            .catch(function() {});
    }

    // Initial timestamp fetch (don't trigger update on first load)
    fetch("/events/poll/")
        .then(function(r) { return r.json(); })
        .then(function(data) { lastTs = data.ts; })
        .catch(function() {});

    setInterval(poll, pollInterval);
})();
