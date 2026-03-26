const map = L.map('map').setView([18.5204, 73.8567], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: 'OSM'
}).addTo(map);
let driverMarker = null;
const driverId = {{ route.assigned_driver.id }};
function updateDriverLocation() {
    fetch(`/routes/driver/location/${driverId}/`)
    .then(res => res.json())
    .then(data => {
        if (!data.latitude) return;
        const latlng = [data.latitude, data.longitude];
        if (!driverMarker) {
            driverMarker = L.marker(latlng).addTo(map)
                .bindPopup("Driver");
        } else {
            driverMarker.setLatLng(latlng);
        }
    });
}
setInterval(updateDriverLocation, 3000);
const routeCoordinates = [
    {% for stop in route.stops.all %}
        [{{ stop.bin.latitude }}, {{ stop.bin.longitude }}],
    {% endfor %}
];
L.polyline(routeCoordinates, {
    color: 'green',
    weight: 4
}).addTo(map);
routeCoordinates.forEach(coord => {
    L.marker(coord).addTo(map);
});