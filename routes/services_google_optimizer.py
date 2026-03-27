import requests
from django.conf import settings
from django.core.cache import cache

def get_distance_matrix(origins, destinations):
    cache_key = f"matrix_{origins}_{destinations}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": "|".join(origins),
        "destinations": "|".join(destinations),
        "key": settings.GOOGLE_MAPS_API_KEY,
        "mode": "driving",
        "departure_time": "now"  # traffic-aware
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    cache.set(cache_key, data, timeout=3600)  # cache 1 hour
    return data

def optimize_with_google(bin_data):
    if not bin_data:
        return [], 0, 0
    depot = f"{settings.DEPOT_LAT},{settings.DEPOT_LNG}"
    unvisited = bin_data.copy()
    route = []
    current = depot
    total_distance = 0
    total_time = 0
    while unvisited:
        destinations = [ f"{b['latitude']},{b['longitude']}" for b in unvisited]
        matrix = get_distance_matrix([current], destinations)
        if not matrix:
            next_bin = unvisited.pop(0)
        else:
            elements = matrix["rows"][0]["elements"]
            min_index = min(range(len(elements)),key=lambda i: elements[i]["duration"]["value"])
            best = elements[min_index]
            total_distance += best["distance"]["value"] / 1000
            total_time += best["duration"]["value"] / 60
            next_bin = unvisited.pop(min_index)
        route.append(next_bin)
        current = f"{next_bin['latitude']},{next_bin['longitude']}"
    return route, round(total_distance, 2), int(total_time)