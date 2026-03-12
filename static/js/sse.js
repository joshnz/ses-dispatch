/* Real-time dispatch updates via polling.
   SSE with sync Gunicorn workers holds one thread per connection,
   so we use lightweight polling instead. */
(function() {
    var pollInterval = 5000;
    var lastTs = 0;

    function showPhotoToast(sierra, count) {
        var container = document.getElementById('toast-container');
        if (!container) return;
        var toast = document.createElement('div');
        toast.className = 'toast align-items-center text-bg-info border-0 show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML =
            '<div class="d-flex">' +
            '<div class="toast-body">' +
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16">' +
            '<path d="M4.502 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/>' +
            '<path d="M14.002 13a2 2 0 0 1-2 2h-10a2 2 0 0 1-2-2V5A2 2 0 0 1 2 3h10a2 2 0 0 1 2 2v8zm-10.44-5a.5.5 0 0 0-.389.188l-2.173 2.7V13a1 1 0 0 0 1 1h10a1 1 0 0 0 .971-.757L9.168 8.85a.5.5 0 0 0-.764-.07L5.965 11.22a.5.5 0 0 1-.764-.07L3.562 8.19z"/>' +
            '</svg>' +
            '<strong>New photo</strong> uploaded for ' + sierra + ' (' + count + ' total)' +
            '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            '</div>';
        container.appendChild(toast);
        // Auto-dismiss after 8 seconds
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() { toast.remove(); }, 300);
        }, 8000);
    }

    function poll() {
        fetch("/events/poll/?since=" + lastTs)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.ts > lastTs) {
                    lastTs = data.ts;
                    if (lastTs > 0) {
                        htmx.trigger(document.body, "dispatch-changed");
                    }
                }
                if (data.photo_uploads) {
                    data.photo_uploads.forEach(function(p) {
                        showPhotoToast(p.sierra, p.count);
                    });
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
