# utils/data_parser.py - Clean Data Parsers
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FlightParser:
    """Parser for Skyscanner flight data"""
    
    def parse_flights(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse Skyscanner flight data from Apify
        
        Args:
            raw_data: Raw response from jupri/skyscanner-flight actor
            
        Returns:
            List of parsed flight dictionaries
        """
        flights = []
        
        try:
            for item in raw_data:
                if not isinstance(item, dict):
                    continue
                    
                # Extract lookup tables
                carriers = item.get('_carriers', {})
                legs = item.get('legs', [])
                pricing_options = item.get('pricing_options', [])
                
                if not legs or not pricing_options:
                    continue
                
                # Process each pricing option
                for pricing_option in pricing_options[:5]:  # Limit to 5 per item
                    flight = self._parse_single_flight(pricing_option, legs[0], carriers)
                    if flight and flight['price'] > 0:
                        flights.append(flight)
                
                # Stop after enough flights
                if len(flights) >= 10:
                    break
            
            logger.info(f"Parsed {len(flights)} flights from {len(raw_data)} raw items")
            return flights
            
        except Exception as e:
            logger.error(f"Flight parsing error: {e}")
            return []
    
    def _parse_single_flight(
        self, 
        pricing_option: Dict[str, Any], 
        leg: Dict[str, Any], 
        carriers: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse a single flight from pricing option and leg data"""
        try:
            # Extract price
            price_info = pricing_option.get('price', {})
            price = price_info.get('amount', 0)
            
            # Extract airline
            airline = self._extract_airline(leg, carriers)
            
            # Extract timing and duration
            departure_time = leg.get('departure', 'Unknown')
            formatted_time = self._format_time(departure_time)
            
            duration_minutes = leg.get('duration', 0)
            formatted_duration = self._format_duration(duration_minutes)
            
            # Extract stops
            stop_count = leg.get('stop_count', 0)
            
            # Extract booking URL
            booking_url = self._extract_booking_url(pricing_option)
            
            return {
                'airline': airline,
                'price': int(price) if price else 0,
                'time': formatted_time,
                'duration': formatted_duration,
                'stops': stop_count,
                'source': 'Skyscanner',
                'url': booking_url,
                'date': departure_time.split('T')[0] if 'T' in str(departure_time) else ''
            }
            
        except Exception as e:
            logger.warning(f"Error parsing single flight: {e}")
            return None
    
    def _extract_airline(self, leg: Dict[str, Any], carriers: Dict[str, Any]) -> str:
        """Extract airline name from leg and carriers data"""
        try:
            marketing_carrier_ids = leg.get('marketing_carrier_ids', [])
            if marketing_carrier_ids and carriers:
                carrier_id = str(marketing_carrier_ids[0])
                if carrier_id in carriers:
                    return carriers[carrier_id].get('name', 'Unknown')
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def _extract_booking_url(self, pricing_option: Dict[str, Any]) -> str:
        """Extract booking URL from pricing option"""
        try:
            items = pricing_option.get('items', [])
            if items and len(items) > 0:
                raw_url = items[0].get('url', '')
                if raw_url.startswith('/transport_deeplink/'):
                    return 'https://www.skyscanner.com' + raw_url
                return raw_url[:200]  # Limit URL length
            return ""
        except Exception:
            return ""
    
    def _format_time(self, iso_time_str: str) -> str:
        """Convert ISO timestamp to HH:MM format"""
        try:
            if not iso_time_str or iso_time_str == 'Unknown':
                return 'Unknown'
            
            # Try different ISO formats
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%SZ']:
                try:
                    dt = datetime.strptime(iso_time_str.replace('Z', ''), fmt.replace('Z', ''))
                    return dt.strftime('%H:%M')
                except ValueError:
                    continue
            
            # Fallback: extract time part
            if 'T' in iso_time_str:
                time_part = iso_time_str.split('T')[1]
                if ':' in time_part:
                    return time_part[:5]  # HH:MM
            
            return str(iso_time_str)[:5] if iso_time_str else 'Unknown'
            
        except Exception:
            return 'Unknown'
    
    def _format_duration(self, minutes: int) -> str:
        """Convert minutes to h:mm format"""
        try:
            if not minutes or minutes <= 0:
                return 'Unknown'
            
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins:02d}m"
            
        except Exception:
            return 'Unknown'

class HotelParser:
    """Parser for Booking.com hotel data"""
    
    def parse_hotels(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse hotel data from Booking.com via Apify
        
        Args:
            raw_data: Raw response from voyager/fast-booking-scraper actor
            
        Returns:
            List of parsed hotel dictionaries
        """
        hotels = []
        
        try:
            for item in raw_data[:50]:  # Process up to 50 hotels
                hotel = self._parse_single_hotel(item)
                if hotel and hotel['price'] > 0:
                    hotels.append(hotel)
            
            # Sort by price-to-rating ratio (best value first)
            hotels.sort(key=lambda h: h['price'] / max(h['rating'], 1))
            
            logger.info(f"Parsed {len(hotels)} hotels from {len(raw_data)} raw items")
            return hotels
            
        except Exception as e:
            logger.error(f"Hotel parsing error: {e}")
            return []
    
    def _parse_single_hotel(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single hotel from raw data"""
        try:
            # Extract basic info with safe type conversion
            name = item.get('name', 'Unknown Hotel')
            price = self._safe_float(item.get('price'), 0)
            rating = self._safe_float(item.get('rating'), 0)
            stars = self._safe_float(item.get('stars'), 0)
            
            # Extract location
            location = self._extract_location(item)
            
            # Extract property type and URL
            property_type = item.get('type', 'hotel')
            url = item.get('url', '')
            
            # Calculate final rating
            final_rating = rating if rating > 0 else (stars if stars > 0 else 4.0)
            
            # Check for room prices if main price is 0
            if price <= 0:
                price = self._extract_room_price(item)
            
            return {
                'name': str(name)[:60] if name else 'Unknown Hotel',
                'price': int(price) if price > 0 else 0,
                'rating': round(float(final_rating), 1),
                'location': str(location)[:50] if location else "City Center",
                'type': str(property_type) if property_type else 'hotel',
                'source': 'Booking.com',
                'url': str(url)[:200] if url else '',
                'checkin': item.get('checkInDate', ''),
                'checkout': item.get('checkOutDate', ''),
            }
            
        except Exception as e:
            logger.warning(f"Error parsing hotel: {e}")
            return None
    
    def _extract_location(self, item: Dict[str, Any]) -> str:
        """Extract location information from hotel data"""
        location = "City Center"  # Default
        
        if 'address' in item and item['address']:
            address = item['address']
            if isinstance(address, dict):
                location = address.get('full', address.get('city', 'City Center'))
            elif isinstance(address, str):
                location = address
        elif 'location' in item:
            location = item.get('location', 'City Center')
        
        return location
    
    def _extract_room_price(self, item: Dict[str, Any]) -> float:
        """Extract minimum room price if main price is not available"""
        if 'rooms' in item and item['rooms']:
            room_prices = []
            for room in item['rooms']:
                if 'options' in room and room['options']:
                    for option in room['options']:
                        try:
                            room_price = float(option.get('price', 0))
                            if room_price > 0:
                                room_prices.append(room_price)
                        except (ValueError, TypeError):
                            continue
            if room_prices:
                return min(room_prices)  # Cheapest room price
        return 0
    
    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float"""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

class AirbnbParser:
    """Parser for Airbnb property data"""
    
    def parse_properties(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse Airbnb properties from raw data
        
        Args:
            raw_data: Raw response from Airbnb scraper actor
            
        Returns:
            List of parsed property dictionaries
        """
        properties = []
        
        try:
            for item in raw_data[:100]:  # Process up to 100 properties
                property_obj = self._parse_single_property(item)
                if property_obj and property_obj['price'] > 0:
                    properties.append(property_obj)
            
            # Sort by price-to-rating ratio
            properties.sort(key=lambda p: p['price'] / max(p['rating'], 1))
            
            logger.info(f"Parsed {len(properties)} Airbnb properties from {len(raw_data)} raw items")
            return properties
            
        except Exception as e:
            logger.error(f"Airbnb parsing error: {e}")
            return []
    
    def _parse_single_property(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse a single Airbnb property"""
        try:
            # Extract name and price
            name = item.get('name', item.get('title', 'Unknown Property'))
            price_per_night = self._extract_price(item)
            
            # Extract rating
            rating, review_count = self._extract_rating(item)
            
            # Extract property details
            room_type = item.get('roomType', 'entire_home')
            property_type = self._map_room_type(room_type)
            
            # Extract location and capacity
            location = self._extract_location_airbnb(item)
            person_capacity = self._extract_capacity(item)
            
            # Extract additional info
            url = item.get('url', '')
            badges = item.get('badges', [])
            
            return {
                'name': str(name)[:60] if name else 'Unknown Property',
                'price': int(price_per_night) if price_per_night > 0 else 0,
                'rating': round(float(rating), 1),
                'review_count': review_count,
                'location': location[:50],
                'property_type': str(property_type)[:30],
                'person_capacity': min(person_capacity, 12),
                'badges': badges,
                'url': str(url)[:300] if url else '',
                'source': 'Airbnb',
                'type': 'airbnb'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing Airbnb property: {e}")
            return None
    
    def _extract_price(self, item: Dict[str, Any]) -> float:
        """Extract price per night from Airbnb data"""
        pricing_data = item.get('pricing', {})
        if isinstance(pricing_data, dict):
            price_str = pricing_data.get('price', '€ 0')
            try:
                # Remove currency symbols and extract number
                price_clean = price_str.replace('€', '').replace('$', '').replace(',', '').replace('\xa0', '').strip()
                return float(price_clean) if price_clean else 0
            except (ValueError, TypeError):
                return 0
        return 0
    
    def _extract_rating(self, item: Dict[str, Any]) -> tuple[float, int]:
        """Extract rating and review count"""
        rating_data = item.get('rating', {})
        if isinstance(rating_data, dict):
            rating = rating_data.get('average', 4.0)
            review_count = rating_data.get('reviewsCount', 0)
            
            try:
                rating = float(rating) if rating is not None else 4.0
                review_count = int(review_count) if review_count is not None else 0
            except (ValueError, TypeError):
                rating = 4.0
                review_count = 0
                
            return rating, review_count
        return 4.0, 0
    
    def _map_room_type(self, room_type: str) -> str:
        """Map room type to display string"""
        type_map = {
            'entire_home': 'Entire home',
            'private_room': 'Private room', 
            'shared_room': 'Shared room',
            'hotel_room': 'Hotel room'
        }
        return type_map.get(room_type, 'Entire home')
    
    def _extract_location_airbnb(self, item: Dict[str, Any]) -> str:
        """Extract location from Airbnb data"""
        if 'coordinates' in item and item['coordinates']:
            coords = item['coordinates']
            lat = coords.get('latitude', 0)
            lon = coords.get('longitude', 0)
            if lat and lon:
                return f"Lat: {lat:.3f}, Lon: {lon:.3f}"
        return 'City Center'
    
    def _extract_capacity(self, item: Dict[str, Any]) -> int:
        """Extract person capacity from subtitles"""
        subtitles = item.get('subtitles', [])
        
        for subtitle in subtitles:
            if 'bed' in subtitle.lower():
                try:
                    import re
                    numbers = re.findall(r'\d+', subtitle)
                    if numbers:
                        return int(numbers[0]) * 2  # Assume 2 people per bed
                except:
                    pass
        
        return 2  # Default capacity