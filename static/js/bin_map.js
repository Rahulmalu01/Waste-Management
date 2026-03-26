document.addEventListener("DOMContentLoaded", () => {
    const bins = JSON.parse(document.getElementById('bins-data').textContent);
    const defaultLat = bins.length ? parseFloat(bins[0].latitude) : 18.5204;
    const defaultLng = bins.length ? parseFloat(bins[0].longitude) : 73.8567;
    const map = L.map('map').setView([defaultLat, defaultLng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    function getMarkerClass(status) {
        if (status === 'FULL') return 'marker-full';
        if (status === 'PARTIAL') return 'marker-partial';
        if (status === 'OFFLINE') return 'marker-offline';
        return 'marker-empty';
    }
    const bounds = [];
    bins.forEach(bin => {
        const lat = parseFloat(bin.latitude);
        const lng = parseFloat(bin.longitude);
        if (isNaN(lat) || isNaN(lng)) return;
        const icon = L.divIcon({
            html: `<div class="custom-marker ${getMarkerClass(bin.status)}"></div>`,
            className: '',
            iconSize: [18, 18],
            iconAnchor: [9, 9],
            popupAnchor: [0, -10]
        });
        const popupContent = `
            <div style="min-width: 220px; font-size: 13px;">
                <h3 style="font-weight: 600; margin-bottom: 6px;">${bin.name}</h3>
                <p><strong>ID:</strong> ${bin.bin_id}</p>
                <p><strong>Fill:</strong> ${bin.fill_percentage}%</p>
                <p><strong>Status:</strong> ${bin.status}</p>
                <p><strong>Location:</strong> ${bin.location_name || '-'}</p>
                <p style="margin-top:6px; color:gray;"><small>Last Seen: ${bin.last_seen || '-'}</small></p>
            </div>
        `;
        L.marker([lat, lng], { icon })
            .addTo(map)
            .bindPopup(popupContent);
        bounds.push([lat, lng]);
    });
    if (bounds.length > 1) {
        map.fitBounds(bounds, { padding: [30, 30] });
    }
});