# simple_city_resolver.py - Smart & Simple City Resolution
import asyncio
import json
import os
from typing import Optional, Dict, List
import httpx

class SimpleCityResolver:
    """
    Smart & Simple approach:
    1. In-memory cache for speed (no external dependencies)
    2. Geocoding + nearest airport for any location
    3. Minimal hardcoding - only the most essential
    """
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.airport_db = self._load_airport_database()
        self.common_cities = self._load_common_cities()
    
    def _load_airport_database(self) -> Dict:
        """Essential airports only - smart selection"""
        return {
            # Major European hubs (most flight connections)
            'VIE': {'name': 'Vienna', 'lat': 48.1103, 'lon': 16.5697, 'country': 'Austria'},
            'MUC': {'name': 'Munich', 'lat': 48.3538, 'lon': 11.7861, 'country': 'Germany'},
            'FRA': {'name': 'Frankfurt', 'lat': 50.0264, 'lon': 8.5431, 'country': 'Germany'},
            'CDG': {'name': 'Paris', 'lat': 49.0097, 'lon': 2.5479, 'country': 'France'},
            'LHR': {'name': 'London', 'lat': 51.4700, 'lon': -0.4543, 'country': 'UK'},
            'AMS': {'name': 'Amsterdam', 'lat': 52.3105, 'lon': 4.7683, 'country': 'Netherlands'},
            'ZUR': {'name': 'Zurich', 'lat': 47.4647, 'lon': 8.5492, 'country': 'Switzerland'},
            
            # Austrian airports (your market)
            'GRZ': {'name': 'Graz', 'lat': 46.9911, 'lon': 15.4396, 'country': 'Austria'},
            'SZG': {'name': 'Salzburg', 'lat': 47.7933, 'lon': 13.0043, 'country': 'Austria'},
            'INN': {'name': 'Innsbruck', 'lat': 47.2602, 'lon': 11.3439, 'country': 'Austria'},
            'KLU': {'name': 'Klagenfurt', 'lat': 46.6425, 'lon': 14.3376, 'country': 'Austria'},
            'LNZ': {'name': 'Linz', 'lat': 48.2332, 'lon': 14.1875, 'country': 'Austria'},
            
            # Popular destinations (vacation spots)
            'BCN': {'name': 'Barcelona', 'lat': 41.2974, 'lon': 2.0833, 'country': 'Spain'},
            'MAD': {'name': 'Madrid', 'lat': 40.4719, 'lon': -3.5626, 'country': 'Spain'},
            'PMI': {'name': 'Palma', 'lat': 39.5517, 'lon': 2.7388, 'country': 'Spain'},
            'IBZ': {'name': 'Ibiza', 'lat': 38.8728, 'lon': 1.3731, 'country': 'Spain'},
            'FCO': {'name': 'Rome', 'lat': 41.8003, 'lon': 12.2389, 'country': 'Italy'},
            'MXP': {'name': 'Milan', 'lat': 45.6306, 'lon': 8.7281, 'country': 'Italy'},
            'VCE': {'name': 'Venice', 'lat': 45.5053, 'lon': 12.3519, 'country': 'Italy'},
            'BRU': {'name': 'Brussels', 'lat': 50.9014, 'lon': 4.4844, 'country': 'Belgium'},
            'PRG': {'name': 'Prague', 'lat': 50.1008, 'lon': 14.2632, 'country': 'Czech Republic'},
            'BUD': {'name': 'Budapest', 'lat': 47.4398, 'lon': 19.2611, 'country': 'Hungary'},
            
            # Neighboring countries (likely destinations from Austria)
            'LJU': {'name': 'Ljubljana', 'lat': 46.2237, 'lon': 14.4576, 'country': 'Slovenia'},
            'ZAG': {'name': 'Zagreb', 'lat': 45.7429, 'lon': 16.0688, 'country': 'Croatia'},
            'SPU': {'name': 'Split', 'lat': 43.5392, 'lon': 16.2981, 'country': 'Croatia'},
            'DBV': {'name': 'Dubrovnik', 'lat': 42.5614, 'lon': 18.2682, 'country': 'Croatia'},
            
            # Long-haul popular
            'JFK': {'name': 'New York', 'lat': 40.6413, 'lon': -73.7781, 'country': 'USA'},
            'DXB': {'name': 'Dubai', 'lat': 25.2532, 'lon': 55.3657, 'country': 'UAE'},
            'BKK': {'name': 'Bangkok', 'lat': 13.6900, 'lon': 100.7501, 'country': 'Thailand'},
            'NRT': {'name': 'Tokyo', 'lat': 35.7720, 'lon': 140.3929, 'country': 'Japan'}
        }
    
    def _load_common_cities(self) -> Dict:
        """Only the most essential city mappings - curated for quality"""
        return {
            # Direct IATA matches
            'vie': 'VIE', 'vienna': 'VIE', 'wien': 'VIE',
            'grz': 'GRZ', 'graz': 'GRZ',
            'muc': 'MUC', 'munich': 'MUC', 'münchen': 'MUC',
            'fra': 'FRA', 'frankfurt': 'FRA',
            'cdg': 'CDG', 'paris': 'CDG',
            'lhr': 'LHR', 'london': 'LHR',
            'bcn': 'BCN', 'barcelona': 'BCN',
            'pmi': 'PMI', 'palma': 'PMI', 'mallorca': 'PMI',
            'ibz': 'IBZ', 'ibiza': 'IBZ',
            'fco': 'FCO', 'rome': 'FCO', 'rom': 'FCO',
            
            # Key vacation spots on islands (hardest to geocode correctly)
            'port de soller': 'PMI',
            'alcudia': 'PMI',
            'magaluf': 'PMI',
            'cala millor': 'PMI',
            'santorini': 'JTR',
            'mykonos': 'JMK',
            'rhodes': 'RHO',
            
            # Common misspellings/variations
            'ny': 'JFK', 'new york': 'JFK', 'nyc': 'JFK',
            'la': 'LAX', 'los angeles': 'LAX',
            'dubai': 'DXB',
            'tokyo': 'NRT'
        }
    
    async def resolve_to_iata(self, location: str) -> Optional[str]:
        """
        Smart & Simple resolution:
        1. Check cache (fast)
        2. Check common cities (curated quality)
        3. Geocode + find nearest airport (handles everything else)
        """
        if not location or not location.strip():
            return None
        
        # Normalize input
        normalized = self._normalize(location)
        
        # 1. Cache hit (fast path)
        if normalized in self.cache:
            print(f"✅ Cache hit: {location} → {self.cache[normalized]}")
            return self.cache[normalized]
        
        # 2. Common cities (curated quality)
        if normalized in self.common_cities:
            iata = self.common_cities[normalized]
            self.cache[normalized] = iata  # Cache for next time
            print(f"✅ Common city: {location} → {iata}")
            return iata
        
        # 3. Check if it's already an IATA code
        if len(normalized) == 3 and normalized.upper() in self.airport_db:
            iata = normalized.upper()
            self.cache[normalized] = iata
            print(f"✅ Direct IATA: {location} → {iata}")
            return iata
        
        # 4. Geocode + nearest airport (handles everything else)
        print(f"🌍 Geocoding: {location}")
        nearest_iata = await self._find_nearest_airport(location)
        
        if nearest_iata:
            self.cache[normalized] = nearest_iata  # Cache for next time
            print(f"✅ Nearest airport: {location} → {nearest_iata}")
            return nearest_iata
        
        print(f"❌ Could not resolve: {location}")
        return None
    
    def _normalize(self, city: str) -> str:
        """Simple but effective normalization"""
        city = city.lower().strip()
        
        # Handle common special characters
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
        
        # Remove special chars, normalize spaces
        import re
        city = re.sub(r'[^\w\s]', ' ', city)
        city = re.sub(r'\s+', ' ', city).strip()
        
        return city
    
    async def _find_nearest_airport(self, location: str) -> Optional[str]:
        """Geocode location and find nearest airport"""
        try:
            # Geocode using OpenStreetMap (free, no API key needed)
            coords = await self._geocode(location)
            if not coords:
                return None
            
            # Find nearest airport
            nearest = self._calculate_nearest_airport(coords['lat'], coords['lon'])
            return nearest
            
        except Exception as e:
            print(f"❌ Geocoding error: {e}")
            return None
    
    async def _geocode(self, location: str) -> Optional[Dict]:
        """Simple geocoding using OpenStreetMap"""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': location,
                'format': 'json',
                'limit': 1
            }
            headers = {
                'User-Agent': 'HolidayEngine/1.0'
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        result = data[0]
                        return {
                            'lat': float(result['lat']),
                            'lon': float(result['lon']),
                            'display_name': result.get('display_name', location)
                        }
            
            return None
            
        except Exception as e:
            print(f"❌ Geocoding failed: {e}")
            return None
    
    def _calculate_nearest_airport(self, lat: float, lon: float) -> Optional[str]:
        """Find nearest airport using simple distance calculation"""
        import math
        
        def distance(lat1, lon1, lat2, lon2):
            # Haversine formula
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            return c * 6371  # Earth radius in km
        
        nearest_airport = None
        nearest_distance = float('inf')
        
        for iata, airport in self.airport_db.items():
            dist = distance(lat, lon, airport['lat'], airport['lon'])
            
            if dist < nearest_distance:
                nearest_distance = dist
                nearest_airport = iata
        
        # Only return if within reasonable distance (1000km)
        if nearest_distance <= 1000:
            print(f"📍 Nearest airport: {nearest_airport} ({nearest_distance:.1f}km)")
            return nearest_airport
        
        return None
    
    def get_cache_stats(self) -> Dict:
        """Simple diagnostics"""
        return {
            'cache_size': len(self.cache),
            'airports_loaded': len(self.airport_db),
            'common_cities': len(self.common_cities)
        }


# Global instance (simple singleton pattern)
city_resolver = SimpleCityResolver()

async def resolve_city_to_iata(location: str) -> Optional[str]:
    """Simple public API"""
    return await city_resolver.resolve_to_iata(location)


# Test function
async def test_simple_resolver():
    """Test the simplified resolver"""
    test_cases = [
        "Vienna",           # Common city
        "Port de Soller",   # Island location
        "Deutschlandsberg", # Small town → nearest airport
        "VIE",             # Direct IATA
        "New York",        # Common international
        "Nonexistent Place" # Should fail gracefully
    ]
    
    print("🧪 Testing Simple City Resolver:")
    print("=" * 40)
    
    for location in test_cases:
        print(f"\n📍 Testing: '{location}'")
        result = await resolve_city_to_iata(location)
        print(f"   Result: {result or 'None'}")
    
    # Show cache stats
    stats = city_resolver.get_cache_stats()
    print(f"\n📊 Cache stats: {stats}")


if __name__ == "__main__":
    asyncio.run(test_simple_resolver())