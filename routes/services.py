import math
from django.utils import timezone
from bins.models import Bin
from alerts.services import resolve_bin_full_alert
from .models import Route, RouteStop, RouteActivity


# -------------------------------
# BIN FETCH
# -------------------------------
def get_full_bins():
    return Bin.objects.filter(status='FULL', is_active=True)


# -------------------------------
# DATA PREPARATION
# -------------------------------
def prepare_bins_for_optimizer(full_bins):
    return [
        {
            'bin_id': bin_obj.id,
            'bin_code': bin_obj.bin_id,
            'name': bin_obj.name,
            'latitude': bin_obj.latitude,
            'longitude': bin_obj.longitude,
            'fill_percentage': bin_obj.fill_percentage,
            'location_name': bin_obj.location_name,
        }
        for bin_obj in full_bins
    ]


# -------------------------------
# DISTANCE FUNCTION
# -------------------------------
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # km

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


# -------------------------------
# ROUTE DISTANCE (FOR 2-OPT)
# -------------------------------
def route_distance(route):
    total = 0
    for i in range(len(route) - 1):
        total += calculate_distance(
            route[i]['latitude'],
            route[i]['longitude'],
            route[i + 1]['latitude'],
            route[i + 1]['longitude']
        )
    return total


# -------------------------------
# 2-OPT OPTIMIZATION
# -------------------------------
def two_opt(route):
    best = route
    improved = True

    while improved:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best)):
                if j - i == 1:
                    continue

                new_route = best[:]
                new_route[i:j] = best[j - 1:i - 1:-1]

                if route_distance(new_route) < route_distance(best):
                    best = new_route
                    improved = True

        route = best

    return best


# -------------------------------
# MAIN OPTIMIZER
# -------------------------------
def run_trained_route_optimizer(bin_data):
    if not bin_data:
        return {
            'total_distance_km': 0.0,
            'optimized_order': [],
            'raw_output': {'message': 'No bins'}
        }

    depot_lat = 18.5204
    depot_lng = 73.8567

    unvisited = bin_data.copy()
    route = []

    current_lat = depot_lat
    current_lng = depot_lng

    total_distance = 0

    # -------- NEAREST NEIGHBOR --------
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

        route.append(nearest)
        total_distance += min_dist

        current_lat = nearest['latitude']
        current_lng = nearest['longitude']

        unvisited.remove(nearest)

    # -------- 2-OPT IMPROVEMENT --------
    route = two_opt(route)

    # -------- FINAL FORMAT --------
    optimized_order = []
    stop_order = 1

    for bin_obj in route:
        optimized_order.append({
            'stop_order': stop_order,
            'bin_id': bin_obj['bin_id'],
            'bin_code': bin_obj['bin_code'],
            'estimated_arrival': f"{stop_order * 5} min"
        })
        stop_order += 1

    return {
        'total_distance_km': round(total_distance, 2),
        'optimized_order': optimized_order,
        'raw_output': {
            'algorithm': 'nearest_neighbor + 2opt',
            'stops': len(optimized_order)
        }
    }


# -------------------------------
# LOGGING
# -------------------------------
def log_route_activity(route, action, message, user=None, stop=None):
    return RouteActivity.objects.create(
        route=route,
        stop=stop,
        user=user,
        action=action,
        message=message,
    )


# -------------------------------
# ROUTE CREATION
# -------------------------------
def create_optimized_route(created_by=None):
    full_bins = get_full_bins()

    if not full_bins.exists():
        return None, 'No full bins available for route generation.'

    prepared_bins = prepare_bins_for_optimizer(full_bins)
    optimizer_result = run_trained_route_optimizer(prepared_bins)

    if not optimizer_result['optimized_order']:
        return None, 'Optimizer failed to generate route.'

    route = Route.objects.create(
        route_name=f"Route {Route.objects.count() + 1}",
        created_by=created_by,
        total_bins=len(optimizer_result['optimized_order']),
        total_distance_km=optimizer_result.get('total_distance_km', 0.0),
        optimizer_result=optimizer_result.get('raw_output', {})
    )

    bin_map = {bin_obj.id: bin_obj for bin_obj in full_bins}

    stops = []
    for stop in optimizer_result['optimized_order']:
        bin_obj = bin_map.get(stop['bin_id'])

        if not bin_obj:
            continue

        stops.append(
            RouteStop(
                route=route,
                bin=bin_obj,
                stop_order=stop['stop_order'],
                estimated_arrival=stop.get('estimated_arrival')
            )
        )

    RouteStop.objects.bulk_create(stops)

    log_route_activity(
        route=route,
        action='ROUTE_CREATED',
        message=f"{route.route_name} created with {route.total_bins} stops.",
        user=created_by
    )

    update_route_status(route)

    return route, 'Optimized route created successfully.'


# -------------------------------
# BIN RESET
# -------------------------------
def reset_bin_after_collection(bin_obj):
    bin_obj.current_distance_cm = bin_obj.bin_height_cm
    bin_obj.fill_percentage = 0.0
    bin_obj.status = 'EMPTY'
    bin_obj.save()
    return bin_obj


# -------------------------------
# ROUTE STATUS
# -------------------------------
def update_route_status(route):
    stops = route.stops.all()

    total_stops = stops.count()
    collected_stops = stops.filter(status='COLLECTED').count()
    skipped_stops = stops.filter(status='SKIPPED').count()
    pending_stops = stops.filter(status='PENDING').count()

    route.collected_count = collected_stops
    route.skipped_count = skipped_stops
    route.pending_count = pending_stops

    previous_status = route.status

    if total_stops == 0:
        route.status = 'PLANNED'
    elif pending_stops == total_stops:
        route.status = 'ASSIGNED' if route.assigned_driver else 'PLANNED'
    elif pending_stops == 0:
        route.status = 'COMPLETED'
        if not route.completed_at:
            route.completed_at = timezone.now()
    else:
        route.status = 'IN_PROGRESS'
        if not route.started_at:
            route.started_at = timezone.now()

    route.save()

    if route.status == 'COMPLETED' and previous_status != 'COMPLETED':
        log_route_activity(
            route=route,
            action='ROUTE_COMPLETED',
            message=f"Route {route.route_name} completed successfully.",
            user=route.assigned_driver
        )

    return {
        'total_stops': total_stops,
        'collected_stops': collected_stops,
        'skipped_stops': skipped_stops,
        'pending_stops': pending_stops,
        'route_status': route.status,
    }


# -------------------------------
# DRIVER ACTIONS
# -------------------------------
def mark_stop_collected(stop, user=None, reset_bin=False):
    stop.status = 'COLLECTED'
    stop.notes = ((stop.notes or '').strip() + '\nCollected by driver.').strip()
    stop.save()

    resolve_bin_full_alert(stop.bin, resolved_by=user)

    if reset_bin:
        reset_bin_after_collection(stop.bin)

        log_route_activity(
            route=stop.route,
            action='BIN_RESET',
            message=f"Bin {stop.bin.bin_id} reset after collection.",
            user=user,
            stop=stop
        )

    log_route_activity(
        route=stop.route,
        action='STOP_COLLECTED',
        message=f"Stop {stop.stop_order} for bin {stop.bin.bin_id} collected.",
        user=user,
        stop=stop
    )

    return update_route_status(stop.route)


def mark_stop_skipped(stop, user=None, reason=None):
    stop.status = 'SKIPPED'
    if reason:
        stop.notes = reason
    stop.save()

    log_route_activity(
        route=stop.route,
        action='STOP_SKIPPED',
        message=f"Stop {stop.stop_order} skipped. Reason: {reason or 'Not provided'}",
        user=user,
        stop=stop
    )

    return update_route_status(stop.route)