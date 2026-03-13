/* Real-time dispatch updates via polling.
   SSE with sync Gunicorn workers holds one thread per connection,
   so we use lightweight polling instead. */
(function() {
    var pollInterval = 5000;
    var lastTs = 0;
    var lastPollTime = Date.now();
    var consecutiveErrors = 0;

    function showToast(message, type) {
        var container = document.getElementById('toast-container');
        if (!container) return;
        var bgClass = 'text-bg-info';
        if (type === 'success') bgClass = 'text-bg-success';
        else if (type === 'warning') bgClass = 'text-bg-warning';
        else if (type === 'danger') bgClass = 'text-bg-danger';

        var toast = document.createElement('div');
        toast.className = 'toast align-items-center ' + bgClass + ' border-0 show';
        toast.setAttribute('role', 'alert');
        toast.innerHTML =
            '<div class="d-flex">' +
            '<div class="toast-body">' + message + '</div>' +
            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>' +
            '</div>';
        container.appendChild(toast);
        setTimeout(function() {
            toast.classList.remove('show');
            setTimeout(function() { toast.remove(); }, 300);
        }, 5000);
    }

    function showPhotoToast(sierra, count) {
        showToast(
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="me-2" viewBox="0 0 16 16">' +
            '<path d="M4.502 9a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z"/>' +
            '<path d="M14.002 13a2 2 0 0 1-2 2h-10a2 2 0 0 1-2-2V5A2 2 0 0 1 2 3h10a2 2 0 0 1 2 2v8zm-10.44-5a.5.5 0 0 0-.389.188l-2.173 2.7V13a1 1 0 0 0 1 1h10a1 1 0 0 0 .971-.757L9.168 8.85a.5.5 0 0 0-.764-.07L5.965 11.22a.5.5 0 0 1-.764-.07L3.562 8.19z"/>' +
            '</svg>' +
            '<strong>New photo</strong> uploaded for ' + sierra + ' (' + count + ' total)',
            'info'
        );
    }

    function updateLastUpdated() {
        var el = document.getElementById('last-updated');
        if (!el) return;
        var secs = Math.round((Date.now() - lastPollTime) / 1000);
        if (secs < 5) {
            el.textContent = 'Last updated: just now';
        } else if (secs < 60) {
            el.textContent = 'Last updated: ' + secs + 's ago';
        } else {
            var mins = Math.floor(secs / 60);
            el.textContent = 'Last updated: ' + mins + 'm ago';
        }
    }

    function updateConnectionStatus(ok) {
        var dot = document.getElementById('connection-dot');
        var label = document.getElementById('connection-label');
        if (!dot || !label) return;
        if (ok) {
            consecutiveErrors = 0;
            dot.className = 'status-dot status-dot-ok';
            label.textContent = 'Connected';
        } else {
            consecutiveErrors++;
            if (consecutiveErrors >= 3) {
                dot.className = 'status-dot status-dot-error';
                label.textContent = 'Disconnected';
            } else {
                dot.className = 'status-dot status-dot-warn';
                label.textContent = 'Reconnecting...';
            }
        }
    }

    function poll() {
        fetch("/events/poll/?since=" + lastTs)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                updateConnectionStatus(true);
                lastPollTime = Date.now();
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
            .catch(function() {
                updateConnectionStatus(false);
            });
    }

    // Initial timestamp fetch (don't trigger update on first load)
    fetch("/events/poll/")
        .then(function(r) { return r.json(); })
        .then(function(data) {
            lastTs = data.ts;
            lastPollTime = Date.now();
            updateConnectionStatus(true);
        })
        .catch(function() {
            updateConnectionStatus(false);
        });

    setInterval(poll, pollInterval);
    setInterval(updateLastUpdated, 1000);

    // Expose showToast globally for use by other scripts
    window.sesShowToast = showToast;
})();
