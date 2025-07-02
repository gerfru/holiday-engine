# test_comparison.py - Compare old vs new approach
import math

def simple_normalize(city: str) -> str:
    """Simple normalization from the new approach"""
    city = city.lower().strip()
    
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 
        'ó': 'o', 'ò': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ç': 'c', 'ñ': 'n'
    }
    
    for old, new in replacements.items():
        city = city.replace(old, new)
    
    import re
    city = re.sub(r'[^\w\s]', ' ', city)
    city = re.sub(r'\s+', ' ', city).strip()
    
    return city

def test_simple_approach():
    """Test the simplified approach"""
    
    # Simple curated common cities (instead of 300+ hardcoded)
    common_cities = {
        'vienna': 'VIE', 'wien': 'VIE',
        'graz': 'GRZ',
        'port de soller': 'PMI', 'palma': 'PMI', 'mallorca': 'PMI',
        'barcelona': 'BCN',
        'paris': 'CDG',
        'london': 'LHR'
    }
    
    # Essential airports (instead of 70+)
    airports = {
        'VIE': {'name': 'Vienna', 'lat': 48.1103, 'lon': 16.5697},
        'GRZ': {'name': 'Graz', 'lat': 46.9911, 'lon': 15.4396},
        'PMI': {'name': 'Palma', 'lat': 39.5517, 'lon': 2.7388},
        'BCN': {'name': 'Barcelona', 'lat': 41.2974, 'lon': 2.0833},
        'CDG': {'name': 'Paris', 'lat': 49.0097, 'lon': 2.5479},
        'LHR': {'name': 'London', 'lat': 51.4700, 'lon': -0.4543}
    }
    
    def find_nearest_airport(location_name: str, lat: float, lon: float) -> str:
        """Simple nearest airport calculation"""
        def distance(lat1, lon1, lat2, lon2):
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return c * 6371
        
        nearest = None
        nearest_dist = float('inf')
        
        for iata, airport in airports.items():
            dist = distance(lat, lon, airport['lat'], airport['lon'])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = iata
        
        return nearest
    
    def simple_resolve(city_input: str) -> str:
        """Simple resolution logic"""
        normalized = simple_normalize(city_input)
        
        # 1. Check common cities (fast path)
        if normalized in common_cities:
            return common_cities[normalized]
        
        # 2. Check if IATA code
        if len(normalized) == 3 and normalized.upper() in airports:
            return normalized.upper()
        
        # 3. For demo: simulate geocoding + nearest airport
        # (In real app, this would call OpenStreetMap API)
        mock_locations = {
            'deutschlandsberg': (46.8133, 15.2167),  # → should find GRZ
            'puerto de soller': (39.7944, 2.6847),   # → should find PMI
            'times square': (40.7580, -73.9855)      # → should find nearest (none in our small db)
        }
        
        if normalized in mock_locations:
            lat, lon = mock_locations[normalized]
            return find_nearest_airport(normalized, lat, lon)
        
        return None
    
    # Test cases
    test_cases = [
        "Vienna",              # Should hit common_cities
        "Port de Soller",      # Should hit common_cities  
        "VIE",                # Should recognize as IATA
        "Deutschlandsberg",    # Should geocode → GRZ
        "Puerto de Soller",    # Should geocode → PMI  
        "Unknown Place"        # Should fail gracefully
    ]
    
    print("🧪 Testing Simple Approach:")
    print("=" * 40)
    
    for city in test_cases:
        result = simple_resolve(city)
        print(f"'{city}' → {result or 'None'}")
    
    print(f"\n📊 Statistics:")
    print(f"   Common cities: {len(common_cities)} (vs 300+ before)")
    print(f"   Airports: {len(airports)} (vs 70+ before)")
    print(f"   Total LOC: ~150 (vs 650+ before)")
    print(f"   External deps: 1 (httpx only)")

if __name__ == "__main__":
    test_simple_approach()