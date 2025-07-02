# Simple test of nearest airport logic without dependencies
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance using Haversine formula"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371  # Earth radius in km

# Test with known coordinates
deutschlandsberg_coords = (46.8133, 15.2167)  # Approximate coordinates
airports = {
    'GRZ': (46.9911, 15.4396),  # Graz Airport
    'VIE': (48.1103, 16.5697),  # Vienna
    'LJU': (46.2237, 14.4576),  # Ljubljana
    'ZAG': (45.7429, 16.0688),  # Zagreb
    'KLU': (46.6425, 14.3376),  # Klagenfurt
}

print("📍 Testing Deutschlandsberg → Nearest Airport")
print(f"Deutschlandsberg coordinates: {deutschlandsberg_coords}")
print()

distances = []
for iata, (lat, lon) in airports.items():
    dist = calculate_distance(deutschlandsberg_coords[0], deutschlandsberg_coords[1], lat, lon)
    distances.append((iata, dist))
    print(f"{iata}: {dist:.1f} km")

distances.sort(key=lambda x: x[1])
print(f"\n✅ Nearest airport: {distances[0][0]} ({distances[0][1]:.1f} km)")