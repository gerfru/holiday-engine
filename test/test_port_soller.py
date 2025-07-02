# Test Port de Soller nearest airport
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance using Haversine formula"""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371  # Earth radius in km

# Port de Soller coordinates (northwest Mallorca)
port_soller_coords = (39.7944, 2.6847)

# Relevant airports
airports = {
    'PMI': (39.5517, 2.7388),  # Palma de Mallorca
    'BCN': (41.2974, 2.0833),  # Barcelona  
    'IBZ': (38.8728, 1.3731),  # Ibiza
    'VLC': (39.4893, -0.4816), # Valencia
}

print("📍 Testing Port de Soller → Nearest Airport")
print(f"Port de Soller coordinates: {port_soller_coords}")
print()

distances = []
for iata, (lat, lon) in airports.items():
    dist = calculate_distance(port_soller_coords[0], port_soller_coords[1], lat, lon)
    distances.append((iata, dist))
    print(f"{iata}: {dist:.1f} km")

distances.sort(key=lambda x: x[1])
print(f"\n✅ Nearest airport: {distances[0][0]} ({distances[0][1]:.1f} km)")