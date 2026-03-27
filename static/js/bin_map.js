document.addEventListener("DOMContentLoaded", function () {

    const binsElement = document.getElementById("bins-data");

    if (!binsElement) {
        console.error("bins-data not found");
        return;
    }

    const bins = JSON.parse(binsElement.textContent);

    console.log("Bins:", bins);

    // Default location (Pune)
    const defaultLat = bins.length ? parseFloat(bins[0].latitude) : 18.5204;
    const defaultLng = bins.length ? parseFloat(bins[0].longitude) : 73.8567;

    // Initialize map
    const map = L.map('map').setView([defaultLat, defaultLng], 13);

    // Tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Marker color classes
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

        // Marker icon
        const icon = L.divIcon({
            html: `<div class="custom-marker ${getMarkerClass(bin.status)}"></div>`,
            className: '',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        // Popup content
        const popupContent = `
            <div>
                <strong>Bin ID:</strong> ${bin.id || 'N/A'}<br>
                <strong>Status:</strong> ${bin.status}<br>
                <strong>Fill:</strong> ${bin.fill_level || 0}%<br>
                <strong>Lat:</strong> ${lat}<br>
                <strong>Lng:</strong> ${lng}
            </div>
        `;

        L.marker([lat, lng], { icon })
            .addTo(map)
            .bindPopup(popupContent);

        bounds.push([lat, lng]);
    });

    // Auto zoom
    if (bounds.length > 1) {
        map.fitBounds(bounds);
    }

});