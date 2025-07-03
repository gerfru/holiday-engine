# services/city_resolver.py - Improved City Resolution with Real Airport Data
from typing import Optional, Tuple, List, Dict, Any
import asyncio
import logging
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from difflib import SequenceMatcher
import os

logger = logging.getLogger(__name__)

class CityResolverService:
    """Service for resolving city names to IATA airport codes using real airport data"""
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.airports_df = None
        self.common_cities = self._load_common_cities()
        self.geolocator = Nominatim(user_agent="HolidayEngine/2.0")
        
        # Load airports on initialization
        self._load_airports()
    
    def _load_airports(self):
        """Load and prepare airports database"""
        try:
            # Try multiple possible locations for airports.csv
            possible_paths = [
                "airports.csv",                    # Root directory
                "config/airports.csv",             # Config directory  
                os.path.join("config", "airports.csv"),  # Explicit config path
                os.path.join(os.path.dirname(__file__), "..", "config", "airports.csv")  # Relative to this file
            ]
            
            airports_file = None
            for path in possible_paths:
                if os.path.exists(path):
                    airports_file = path
                    break
            
            # DEBUG: Check if file exists
            if not airports_file:
                logger.error(f"airports.csv not found in any of these locations:")
                for path in possible_paths:
                    abs_path = os.path.abspath(path)
                    exists = "✅" if os.path.exists(path) else "❌"
                    logger.error(f"  {exists} {abs_path}")
                logger.error(f"Current working directory: {os.getcwd()}")
                logger.error(f"Files in current directory: {os.listdir('.')}")
                if os.path.exists('config'):
                    logger.error(f"Files in config/: {os.listdir('config')}")
                return
            
            logger.info(f"Loading airports database from: {os.path.abspath(airports_file)}")
            
            # Load all airports
            self.airports_df = pd.read_csv(airports_file)
            logger.info(f"Loaded {len(self.airports_df)} total airports from CSV")
            
            # Filter to passenger airports only
            passenger_types = ['large_airport', 'medium_airport', 'small_airport']
            before_filter = len(self.airports_df)
            
            self.airports_df = self.airports_df[
                self.airports_df['type'].isin(passenger_types) &
                self.airports_df['scheduled_service'].eq('yes') &
                self.airports_df['iata_code'].notna()  # Must have IATA code
            ].copy()
            
            # Clean up data
            self.airports_df['iata_code'] = self.airports_df['iata_code'].str.upper()
            
            after_filter = len(self.airports_df)
            logger.info(f"Filtered from {before_filter} to {after_filter} passenger airports with IATA codes")
            
            # DEBUG: Show some examples
            if not self.airports_df.empty:
                sample_airports = self.airports_df.head(3)
                logger.info("Sample airports loaded:")
                for _, airport in sample_airports.iterrows():
                    logger.info(f"  {airport['iata_code']}: {airport['name']} ({airport['municipality']})")
            
        except Exception as e:
            logger.error(f"Failed to load airports database: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.airports_df = None
    
    async def resolve_to_iata(self, location: str) -> Tuple[Optional[str], str, List[str]]:
        """
        Resolve city name to IATA code with suggestions
        
        Args:
            location: City name or IATA code
            
        Returns:
            Tuple of (IATA_code, recognized_city, suggestions)
        """
        if not location or not location.strip():
            return None, "", []
        
        logger.info(f"Resolving city: {location}")
        
        # Normalize input
        normalized = self._normalize(location)
        
        # 1. Cache hit (fast path)
        if normalized in self.cache:
            logger.debug(f"Cache hit: {location} → {self.cache[normalized]}")
            return self.cache[normalized], location.title(), []
        
        # 2. Common cities (curated quality)
        if normalized in self.common_cities:
            iata = self.common_cities[normalized]
            self.cache[normalized] = iata
            logger.info(f"Common city match: {location} → {iata}")
            return iata, location.title(), []
        
        # 3. Check if it's already an IATA code
        if len(normalized) == 3 and self._is_valid_iata(normalized.upper()):
            iata = normalized.upper()
            self.cache[normalized] = iata
            logger.info(f"Direct IATA: {location} → {iata}")
            return iata, location.title(), []
        
        # 4. Geocode + nearest airport using real data
        logger.info(f"Geocoding: {location}")
        nearest_iata = await self._find_nearest_airport_real(location)
        
        if nearest_iata:
            self.cache[normalized] = nearest_iata
            airport_info = self._get_airport_info(nearest_iata)
            city_name = airport_info.get('municipality', location.title())
            logger.info(f"Nearest airport: {location} → {nearest_iata} ({city_name})")
            return nearest_iata, city_name, []
        
        # 5. Generate suggestions for failed lookups
        suggestions = self._get_suggestions(location)
        logger.warning(f"Could not resolve: {location}. Suggestions: {suggestions}")
        return None, location.title(), suggestions
    
    def _is_valid_iata(self, iata_code: str) -> bool:
        """Check if IATA code exists in our database"""
        if self.airports_df is None:
            return False
        return iata_code in self.airports_df['iata_code'].values
    
    def _get_airport_info(self, iata_code: str) -> Dict[str, Any]:
        """Get airport information from database"""
        if self.airports_df is None:
            return {}
        
        airport = self.airports_df[self.airports_df['iata_code'] == iata_code]
        if airport.empty:
            return {}
        
        airport_row = airport.iloc[0]
        return {
            'municipality': airport_row.get('municipality', ''),
            'name': airport_row.get('name', ''),
            'country': airport_row.get('iso_country', ''),
            'latitude': airport_row.get('latitude_deg', 0),
            'longitude': airport_row.get('longitude_deg', 0)
        }
    
    async def _find_nearest_airport_real(self, location: str) -> Optional[str]:
        """Find nearest airport using real geocoding and airport database"""
        try:
            # Geocode the location
            coords = await self._geocode_location(location)
            if not coords:
                return None
            
            # Find nearest airport from real database
            nearest_iata = self._find_nearest_airport_from_coords(
                coords['lat'], coords['lon']
            )
            
            return nearest_iata
            
        except Exception as e:
            logger.error(f"Error finding nearest airport for {location}: {e}")
            return None
    
    async def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """Geocode location using Nominatim"""
        try:
            # Run geocoding in thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            
            def geocode_sync():
                return self.geolocator.geocode(location, timeout=10)
            
            geo_result = await loop.run_in_executor(None, geocode_sync)
            
            if geo_result:
                logger.info(f"Geocoded {location}: {geo_result.latitude:.4f}, {geo_result.longitude:.4f}")
                return {
                    'lat': geo_result.latitude,
                    'lon': geo_result.longitude,
                    'display_name': geo_result.address
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Geocoding failed for {location}: {e}")
            return None
    
    def _find_nearest_airport_from_coords(self, lat: float, lon: float) -> Optional[str]:
        """Find nearest airport from coordinates using real airport database"""
        if self.airports_df is None:
            logger.error("Airport database not loaded!")
            return None
        
        try:
            # Calculate distances to all airports
            def calculate_distance(row):
                try:
                    airport_coords = (row['latitude_deg'], row['longitude_deg'])
                    user_coords = (lat, lon)
                    return geodesic(user_coords, airport_coords).kilometers
                except:
                    return float('inf')  # Invalid coordinates
            
            # Add distance column
            airports_copy = self.airports_df.copy()
            airports_copy['distance_km'] = airports_copy.apply(calculate_distance, axis=1)
            
            # Filter out invalid distances and sort
            valid_airports = airports_copy[airports_copy['distance_km'] < float('inf')]
            
            if valid_airports.empty:
                logger.warning("No valid airports found for distance calculation")
                return None
            
            # Sort by distance and get nearest
            nearest = valid_airports.sort_values('distance_km').iloc[0]
            
            distance = nearest['distance_km']
            iata = nearest['iata_code']
            name = nearest['name']
            
            # IMPROVED: More flexible distance thresholds
            if distance <= 50:
                # Very close - definitely use this airport
                logger.info(f"Found nearby airport: {iata} ({name}) at {distance:.1f}km")
                return iata
            elif distance <= 150:
                # Reasonable distance for major cities
                logger.info(f"Found regional airport: {iata} ({name}) at {distance:.1f}km")
                return iata
            elif distance <= 300:
                # Far but acceptable for small towns
                logger.info(f"Found distant airport: {iata} ({name}) at {distance:.1f}km")
                return iata
            else:
                # Too far - probably wrong
                logger.warning(f"Nearest airport {iata} is too far: {distance:.1f}km")
                return None
            
        except Exception as e:
            logger.error(f"Error calculating nearest airport: {e}")
            return None
    
    def _load_common_cities(self) -> Dict[str, str]:
        """Common city name to IATA mappings for fast lookup"""
        return {
            # Major cities (fast path)
            'vie': 'VIE', 'vienna': 'VIE', 'wien': 'VIE',
            'grz': 'GRZ', 'graz': 'GRZ',
            'muc': 'MUC', 'munich': 'MUC', 'muenchen': 'MUC',
            'fra': 'FRA', 'frankfurt': 'FRA',
            'cdg': 'CDG', 'paris': 'CDG',
            'lhr': 'LHR', 'london': 'LHR',
            'bcn': 'BCN', 'barcelona': 'BCN',
            'mad': 'MAD', 'madrid': 'MAD',
            'fco': 'FCO', 'rome': 'FCO', 'rom': 'FCO',
            
            # Greek destinations (commonly searched)
            'athens': 'ATH', 'athen': 'ATH',
            'rhodes': 'RHO', 'rhodos': 'RHO',
            'santorini': 'JTR', 'thira': 'JTR',
            'mykonos': 'JMK',
            'corfu': 'CFU', 'korfu': 'CFU',
            'crete': 'HER', 'kreta': 'HER',
            
            # Spanish islands
            'pmi': 'PMI', 'palma': 'PMI', 'mallorca': 'PMI',
            'ibz': 'IBZ', 'ibiza': 'IBZ',
            'port de soller': 'PMI',
            'alcudia': 'PMI',
            
            # Common international
            'ny': 'JFK', 'new york': 'JFK', 'nyc': 'JFK',
            'dubai': 'DXB',
            'tokyo': 'NRT',
            'bangkok': 'BKK'
        }
    
    def _normalize(self, city: str) -> str:
        """Normalize city name for consistent matching"""
        city = city.lower().strip()
        
        # Handle special characters
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
    
    def _get_suggestions(self, city_input: str) -> List[str]:
        """Generate suggestions using airport database"""
        suggestions = []
        
        if self.airports_df is None:
            # Fallback to hardcoded list
            popular_cities = [
                "Vienna", "Graz", "Munich", "Frankfurt", "Paris", "London",
                "Barcelona", "Madrid", "Rome", "Athens", "Rhodes"
            ]
        else:
            # Use real airport data for suggestions
            major_airports = self.airports_df[
                self.airports_df['type'] == 'large_airport'
            ]['municipality'].unique()[:20]
            popular_cities = [city for city in major_airports if pd.notna(city)]
        
        city_lower = city_input.lower()
        
        for city in popular_cities:
            if pd.isna(city):
                continue
                
            similarity = SequenceMatcher(None, city_lower, city.lower()).ratio()
            
            # Boost score for partial matches
            if city_lower in city.lower() or city.lower() in city_lower:
                similarity = max(similarity, 0.7)
            
            if similarity > 0.5:
                suggestions.append(str(city))
        
        # Sort by similarity and return top 5
        suggestions.sort(key=lambda x: SequenceMatcher(None, city_lower, x.lower()).ratio(), reverse=True)
        return suggestions[:5]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = {
            'cache_size': len(self.cache),
            'common_cities': len(self.common_cities),
            'airports_loaded': len(self.airports_df) if self.airports_df is not None else 0
        }
        
        if self.airports_df is not None:
            stats.update({
                'large_airports': len(self.airports_df[self.airports_df['type'] == 'large_airport']),
                'medium_airports': len(self.airports_df[self.airports_df['type'] == 'medium_airport']),
                'small_airports': len(self.airports_df[self.airports_df['type'] == 'small_airport'])
            })
        
        return stats