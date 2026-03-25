import math

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(math.radians(lat1)) *
        math.cos(math.radians(lat2)) *
        math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def run_trained_route_optimizer(bin_data):
    if not bin_data:
        return {
            'total_distance_km': 0.0,
            'optimized_order': [],
            'raw_output': {'message': 'No bins'}
        }
    # Depot (you can move to settings)
    depot_lat = 18.5204
    depot_lng = 73.8567
    unvisited = bin_data.copy()
    route = []
    current_lat = depot_lat
    current_lng = depot_lng
    total_distance = 0
    stop_order = 1
    while unvisited:
        nearest = None
        min_dist = float('inf')
        for b in unvisited:
            dist = calculate_distance(
                current_lat,
                current_lng,
                b['latitude'],
                b['longitude']
            )
            if dist < min_dist:
                min_dist = dist
                nearest = b
        total_distance += min_dist
        route.append({
            'stop_order': stop_order,
            'bin_id': nearest['bin_id'],  # IMPORTANT: matches your code
            'bin_code': nearest['bin_code'],
            'estimated_arrival': f"{stop_order * 5} min"
        })
        current_lat = nearest['latitude']
        current_lng = nearest['longitude']
        unvisited.remove(nearest)
        stop_order += 1
    return {
        'total_distance_km': round(total_distance, 2),
        'optimized_order': route,
        'raw_output': {
            'algorithm': 'nearest_neighbor',
            'stops': len(route)
        }
    }