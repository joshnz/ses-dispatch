/* Leaflet map for dispatch dashboard */
(function() {
    const map = L.map('dispatch-map').setView([-37.7990, 144.8880], 13);

    L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        {
            attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
            maxZoom: 19
        }
    ).addTo(map);

    // Load SES coverage area if available
    fetch('/static/data/ses_coverage.geojson')
        .then(r => {
            if (r.ok) return r.json();
            return null;
        })
        .then(data => {
            if (data) {
                L.geoJSON(data, {
                    style: { color: '#E65100', weight: 2, fillOpacity: 0.05 }
                }).addTo(map);
            }
        })
        .catch(() => {});

    // Marker layers
    let jobMarkers = L.layerGroup().addTo(map);
    let crewMarkers = L.layerGroup().addTo(map);
    let dispatchLines = L.layerGroup().addTo(map);

    const priorityColors = { 1: '#d32f2f', 2: '#f57c00', 3: '#1976d2' };
    const statusColors = {
        available: '#2e7d32', dispatched: '#f57c00',
        on_scene: '#d32f2f', returning: '#f57c00', offline: '#9e9e9e'
    };

    function updateMarkers(data) {
        jobMarkers.clearLayers();
        crewMarkers.clearLayers();
        dispatchLines.clearLayers();

        // Job markers (circle markers, color-coded by priority)
        data.jobs.forEach(function(job) {
            const color = priorityColors[job.priority] || '#6c757d';
            const marker = L.circleMarker([job.lat, job.lng], {
                radius: 10, fillColor: color, color: color,
                weight: 2, fillOpacity: 0.7
            }).addTo(jobMarkers);

            marker.bindPopup(
                '<strong>' + job.sierra + '</strong><br>' +
                job.address + '<br>P' + job.priority + ' - ' + job.status
            );

            marker.bindTooltip(job.sierra + ' (P' + job.priority + ')', {
                permanent: false, direction: 'top', offset: [0, -10]
            });

            // Dispatch lines from assigned crews to job
            job.assigned_crews.forEach(function(crew) {
                L.polyline(
                    [[crew.lat, crew.lng], [job.lat, job.lng]],
                    { color: '#f57c00', weight: 2, dashArray: '5,5', opacity: 0.7 }
                ).addTo(dispatchLines)
                    .bindTooltip(crew.callsign);
            });
        });

        // Crew markers (truck icon markers to distinguish from job circles)
        data.crews.forEach(function(crew) {
            const color = statusColors[crew.status] || '#6c757d';
            const icon = L.divIcon({
                className: 'crew-map-icon',
                html: '<div style="background:' + color + ';color:#fff;border:2px solid #fff;border-radius:4px;padding:2px 4px;font-size:14px;line-height:1;box-shadow:0 1px 3px rgba(0,0,0,0.4);display:inline-flex;align-items:center;justify-content:center;">' +
                      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 640 512">' +
                      '<path d="M48 0C21.5 0 0 21.5 0 48V368c0 26.5 21.5 48 48 48H64c0 53 43 96 96 96s96-43 96-96H384c0 53 43 96 96 96s96-43 96-96h32c17.7 0 32-14.3 32-32s-14.3-32-32-32V288 256 237.3c0-17-6.7-33.3-18.7-45.3L512 114.7c-12-12-28.3-18.7-45.3-18.7H416V48c0-26.5-21.5-48-48-48H48zM416 160h50.7L544 237.3V256H416V160zM160 464a48 48 0 1 1 0-96 48 48 0 0 1 0 96zm368-48a48 48 0 1 1 -96 0 48 48 0 1 1 96 0z"/>' +
                      '</svg></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12],
            });
            L.marker([crew.lat, crew.lng], { icon: icon })
                .addTo(crewMarkers)
                .bindTooltip(crew.callsign, { permanent: true, direction: 'top', offset: [0, -15] });
        });
    }

    // Initial load
    fetch('/htmx/map-data/')
        .then(r => r.json())
        .then(data => updateMarkers(data))
        .catch(() => {});

    // SSE-driven updates
    document.body.addEventListener('dispatch-changed', function() {
        fetch('/htmx/map-data/')
            .then(r => r.json())
            .then(data => updateMarkers(data))
            .catch(() => {});
    });
})();
