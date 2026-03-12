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

        // Job markers
        data.jobs.forEach(function(job) {
            const color = priorityColors[job.priority] || '#6c757d';
            const marker = L.circleMarker([job.lat, job.lng], {
                radius: 10, fillColor: color, color: '#fff',
                weight: 2, fillOpacity: 0.8
            }).addTo(jobMarkers);

            marker.bindPopup(
                '<strong>' + job.sierra + '</strong><br>' +
                job.address + '<br>P' + job.priority + ' - ' + job.status
            );

            // Dispatch lines from assigned crews to job
            job.assigned_crews.forEach(function(crew) {
                L.polyline(
                    [[crew.lat, crew.lng], [job.lat, job.lng]],
                    { color: '#f57c00', weight: 2, dashArray: '5,5', opacity: 0.7 }
                ).addTo(dispatchLines)
                    .bindTooltip(crew.callsign);
            });
        });

        // Crew markers
        data.crews.forEach(function(crew) {
            const color = statusColors[crew.status] || '#6c757d';
            L.circleMarker([crew.lat, crew.lng], {
                radius: 7, fillColor: color, color: '#fff',
                weight: 2, fillOpacity: 0.9
            }).addTo(crewMarkers)
                .bindTooltip(crew.callsign, { permanent: true, direction: 'top', offset: [0, -10] });
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
