# travel_api.py - Clean, Robust & Functional Travel APIs
import asyncio
import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# =============================================================================
# FLIGHT SEARCH - jupri/skyscanner-flight Actor
# =============================================================================

async def search_flights_apify(origin: str, destination: str, date: str, max_retries: int = 3):
    """
    Search flights using jupri/skyscanner-flight Apify Actor with retry logic
    
    Args:
        origin (str): IATA airport code (e.g., 'VIE')
        destination (str): IATA airport code (e.g., 'FCO') 
        date (str): Departure date in YYYY-MM-DD format
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        list: List of flight dictionaries with airline, price, time, duration
    """
    print(f"🔍 APIFY FLIGHTS: {origin} → {destination} on {date}")
    
    # Check API token
    if not APIFY_TOKEN:
        print("❌ No APIFY_TOKEN found")
        return []
    
    # Prepare actor input (jupri/skyscanner-flight format)
    actor_input = {
        "origin.0": origin.upper(),
        "target.0": destination.upper(),
        "depart.0": date,
        "market": "DE",
        "currency": "EUR"
    }
    
    for attempt in range(max_retries):
        try:
            print(f"📡 Starting jupri/skyscanner-flight actor (attempt {attempt + 1}/{max_retries})...")
            print(f"📋 Input: {actor_input}")
            
            # Exponential backoff: wait 2^attempt seconds before retry
            if attempt > 0:
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Call Apify API
                response = await client.post(
                    "https://api.apify.com/v2/acts/jupri~skyscanner-flight/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
                    json=actor_input
                )
                
                print(f"🔄 HTTP Status: {response.status_code}")
                
                # Check response status
                if response.status_code not in [200, 201]:
                    print(f"❌ API Error {response.status_code}: {response.text[:500]}")
                    if attempt == max_retries - 1:  # Last attempt
                        raise Exception(f"API returned status {response.status_code} after {max_retries} attempts")
                    continue  # Retry
                
                # Parse response
                data = response.json()
                print(f"✅ API Response: {len(data)} items received")
                
                # Debug first item structure
                if data and len(data) > 0:
                    first_item = data[0]
                    print(f"🔍 Response structure: {list(first_item.keys())[:8]}...")
                
                # Parse flights from response
                flights = _parse_skyscanner_flights(data)
                
                if not flights:
                    print("⚠️ No valid flights found in API response")
                    if attempt == max_retries - 1:  # Last attempt
                        return []
                    continue  # Retry
                
                print(f"✅ Successfully parsed {len(flights)} flights")
                return flights
                
        except asyncio.TimeoutError:
            print(f"⏰ Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise Exception(f"Request timed out after {max_retries} attempts")
            
        except Exception as e:
            print(f"❌ Flight API Error (attempt {attempt + 1}): {e}")
            print(f"❌ Error Type: {type(e).__name__}")
            if attempt == max_retries - 1:  # Last attempt
                raise e
    
    return []  # Should not reach here


def _parse_skyscanner_flights(data):
    """
    Parse jupri/skyscanner-flight response data
    
    Expected structure:
    [
        {
            "_carriers": {...},
            "_places": {...}, 
            "_segments": {...},
            "legs": [...],
            "pricing_options": [...]
        }
    ]
    """
    flights = []
    
    try:
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Extract lookup tables
            carriers = item.get('_carriers', {})
            legs = item.get('legs', [])
            pricing_options = item.get('pricing_options', [])
            
            if not legs or not pricing_options:
                continue
            
            print(f"🔍 Processing: {len(legs)} legs, {len(pricing_options)} pricing options")
            
            # Process each pricing option (= bookable flight)
            for pricing_option in pricing_options[:5]:  # Limit to 5 per item
                try:
                    flight = _parse_single_flight(pricing_option, legs[0], carriers)
                    if flight and flight['price'] > 0:
                        flights.append(flight)
                except Exception as e:
                    print(f"⚠️ Error parsing pricing option: {e}")
                    continue
            
            # Limit total flights
            if len(flights) >= 10:
                break
        
        # Sort by price (cheapest first)
        flights.sort(key=lambda x: x.get('price', 999999))
        return flights[:5]  # Return top 5
        
    except Exception as e:
        print(f"❌ Parser Error: {e}")
        return []


def _parse_single_flight(pricing_option, leg, carriers):
    """Parse a single flight from pricing option and leg data"""
    try:
        # Extract price
        price_info = pricing_option.get('price', {})
        price = price_info.get('amount', 0)
        
        # Extract airline from carriers lookup
        marketing_carrier_ids = leg.get('marketing_carrier_ids', [])
        airline = "Unknown"
        if marketing_carrier_ids and carriers:
            carrier_id = str(marketing_carrier_ids[0])
            if carrier_id in carriers:
                airline = carriers[carrier_id].get('name', 'Unknown')
        
        # Extract timing
        departure_time = leg.get('departure', 'Unknown')
        formatted_time = _format_time(departure_time)
        
        # Extract duration
        duration_minutes = leg.get('duration', 0)
        formatted_duration = _format_duration(duration_minutes)
        
        # Extract stops
        stop_count = leg.get('stop_count', 0)
        stops_text = f" ({stop_count} stops)" if stop_count > 0 else " (nonstop)"
        
        # Extract booking URL (from pricing_option items)
        booking_url = ""
        items = pricing_option.get('items', [])
        if items and len(items) > 0:
            raw_url = items[0].get('url', '')
            # Fix relative URLs to point to Skyscanner
            if raw_url.startswith('/transport_deeplink/'):
                booking_url = 'https://www.skyscanner.com' + raw_url
            else:
                booking_url = raw_url
        
        flight = {
            'airline': airline,
            'price': int(price) if price else 0,
            'time': formatted_time,
            'duration': formatted_duration + stops_text,
            'stops': stop_count,
            'source': 'Skyscanner',
            'url': booking_url[:200] if booking_url else '',  # Limit URL length
            'date': departure_time.split('T')[0] if 'T' in str(departure_time) else ''
        }
        
        print(f"  ✈️ {airline}: {price}€ at {formatted_time} ({formatted_duration})")
        return flight
        
    except Exception as e:
        print(f"❌ Error parsing single flight: {e}")
        return None


def _format_time(iso_time_str):
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
        
        # Fallback: extract time part if possible
        if 'T' in iso_time_str:
            time_part = iso_time_str.split('T')[1]
            if ':' in time_part:
                return time_part[:5]  # HH:MM
        
        return str(iso_time_str)[:5] if iso_time_str else 'Unknown'
        
    except Exception:
        return 'Unknown'


def _format_duration(minutes):
    """Convert minutes to h:mm format"""
    try:
        if not minutes or minutes <= 0:
            return 'Unknown'
        
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins:02d}m"
        
    except Exception:
        return 'Unknown'




# =============================================================================
# HOTEL SEARCH - voyager/booking-scraper Actor  
# =============================================================================

async def search_hotels_apify(city: str, checkin: str, checkout: str, max_retries: int = 3):
    """
    Search hotels using voyager/fast-booking-scraper Apify Actor with retry logic
    
    Args:
        city (str): City name (e.g., 'Barcelona')
        checkin (str): Check-in date in YYYY-MM-DD format
        checkout (str): Check-out date in YYYY-MM-DD format
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        list: List of hotel dictionaries with name, price, rating, location
    """
    print(f"🏨 APIFY HOTELS: {city} ({checkin} - {checkout})")
    
    # Check API token
    if not APIFY_TOKEN:
        print("❌ No APIFY_TOKEN found")
        return []
    
    # Prepare actor input (voyager/fast-booking-scraper format) - request more results
    actor_input = {
        "currency": "EUR",
        "language": "en-us",           # Use proper language code (en-us)
        "maxItems": 200,               # Increase from 20 to 200 for much more results
        "minMaxPrice": "10-1000",      # Reasonable price range
        "search": city,
        "sortBy": "review_score_and_price",  # Better sorting for quality + value
        "starsCountFilter": "any",
        "checkIn": checkin,
        "checkOut": checkout,
        "rooms": 1,
        "adults": 2,
        "children": 0,
        "includeAlternativeAccommodations": True,  # Include apartments, B&Bs, etc.
        "destType": "city"             # Specify we're searching for a city
    }
    
    for attempt in range(max_retries):
        try:
            print(f"📡 Starting voyager/fast-booking-scraper actor (attempt {attempt + 1}/{max_retries})...")
            print(f"📋 Input: {actor_input}")
            
            # Exponential backoff: wait 2^attempt seconds before retry
            if attempt > 0:
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Call Apify API with fast booking scraper
                response = await client.post(
                    "https://api.apify.com/v2/acts/voyager~fast-booking-scraper/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
                    json=actor_input
                )
                
                print(f"🔄 HTTP Status: {response.status_code}")
                
                # Check response status
                if response.status_code not in [200, 201]:
                    print(f"❌ API Error {response.status_code}: {response.text[:500]}")
                    if attempt == max_retries - 1:  # Last attempt
                        raise Exception(f"API returned status {response.status_code} after {max_retries} attempts")
                    continue  # Retry
                
                # Parse response
                data = response.json()
                print(f"✅ API Response: {len(data)} hotels received")
                
                # Debug first item structure
                if data and len(data) > 0:
                    first_item = data[0]
                    print(f"🔍 Response structure: {list(first_item.keys())[:8]}...")
                
                # Parse hotels from response
                hotels = _parse_booking_hotels(data)
                
                if not hotels:
                    print("⚠️ No valid hotels found in API response")
                    if attempt == max_retries - 1:  # Last attempt
                        return []
                    continue  # Retry
                
                print(f"✅ Successfully parsed {len(hotels)} hotels")
                return hotels
                
        except asyncio.TimeoutError:
            print(f"⏰ Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise Exception(f"Request timed out after {max_retries} attempts")
                
        except Exception as e:
            print(f"❌ Hotel API Error (attempt {attempt + 1}): {e}")
            print(f"❌ Error Type: {type(e).__name__}")
            if attempt == max_retries - 1:  # Last attempt
                raise e
    
    return []  # Should not reach here


def _parse_booking_hotels(data):
    """Parse voyager/fast-booking-scraper response data"""
    hotels = []
    
    try:
        for item in data[:50]:  # Process up to 50 best hotels from 200 returned
            try:
                # Extract basic info with safe type conversion
                name = item.get('name', 'Unknown Hotel')
                price = item.get('price')
                rating = item.get('rating')
                stars = item.get('stars')
                
                # Safe numeric conversion
                try:
                    price = float(price) if price is not None else 0
                except (ValueError, TypeError):
                    price = 0
                
                try:
                    rating = float(rating) if rating is not None else 0
                except (ValueError, TypeError):
                    rating = 0
                
                try:
                    stars = float(stars) if stars is not None else 0
                except (ValueError, TypeError):
                    stars = 0
                
                # Extract location safely
                location = "City Center"  # Default
                if 'address' in item and item['address']:
                    address = item['address']
                    if isinstance(address, dict):
                        location = address.get('full', address.get('city', 'City Center'))
                    elif isinstance(address, str):
                        location = address
                elif 'location' in item:
                    location = item.get('location', 'City Center')
                
                # Extract property type
                property_type = item.get('type', 'hotel')
                
                # Extract URL
                url = item.get('url', '')
                
                # Calculate final rating
                final_rating = rating if rating > 0 else (stars if stars > 0 else 4.0)
                
                # Check for room prices if main price is 0 or None
                if price <= 0 and 'rooms' in item and item['rooms']:
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
                        price = min(room_prices)  # Cheapest room price
                
                # Create hotel object with safe values
                hotel = {
                    'name': str(name)[:60] if name else 'Unknown Hotel',
                    'price': int(price) if price > 0 else 0,
                    'rating': round(float(final_rating), 1),
                    'location': str(location)[:50] if location else "City Center",
                    'stars': "⭐" * min(int(final_rating), 5),
                    'url': str(url)[:200] if url else '',
                    'type': str(property_type) if property_type else 'hotel',
                    'source': 'Booking.com',
                    'checkin': item.get('checkInDate', ''),
                    'checkout': item.get('checkOutDate', ''),
                    'search_city': item.get('search', 'Unknown')  # Use search term from input
                }
                
                # Only add hotels with valid data
                if hotel['price'] > 0 and hotel['name'] != 'Unknown Hotel':
                    hotels.append(hotel)
                    print(f"  🏨 {hotel['name'][:35]}: {hotel['price']}€ ⭐{hotel['rating']} ({hotel['type']})")
                
            except Exception as e:
                print(f"⚠️ Error parsing hotel: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Hotel Parser Error: {e}")
    
    # Sort by price-to-rating ratio (best value first)
    if hotels:
        hotels.sort(key=lambda h: h['price'] / max(h['rating'], 1))
    return hotels



# =============================================================================
# AIRBNB SEARCH - Apify Actor Integration
# =============================================================================

async def search_airbnb_apify(city: str, checkin: str, checkout: str, guests: int = 2, max_retries: int = 3):
    """
    Search Airbnb properties using tri_angle/new-fast-airbnb-scraper with retry logic
    
    Args:
        city (str): City name (e.g., 'Barcelona')
        checkin (str): Check-in date in YYYY-MM-DD format
        checkout (str): Check-out date in YYYY-MM-DD format
        guests (int): Number of guests
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        list: List of Airbnb property dictionaries with name, price, rating, etc.
    """
    print(f"🏠 APIFY AIRBNB: {city} ({checkin} - {checkout}) for {guests} guests - LIMITED TO 100 RESULTS")
    
    # Check API token
    if not APIFY_TOKEN:
        print("❌ No APIFY_TOKEN found")
        return []
    
    # Prepare actor input for new-fast-airbnb-scraper (maxItems goes in options!)
    actor_input = {
        "locationQueries": [city],
        "locale": "de-DE",           # German locale
        "currency": "EUR", 
        "checkIn": checkin,
        "checkOut": checkout,
        "adults": guests,
        "children": 0,
        "infants": 0,
        "pets": 0,
        "priceMin": 10,
        "priceMax": 999,
        "maxReviews": 0,             # Skip individual reviews 
        "includeReviews": False      # No review details
    }
    
    for attempt in range(max_retries):
        try:
            print(f"📡 Starting tri_angle/new-fast-airbnb-scraper actor (attempt {attempt + 1}/{max_retries})...")
            print(f"📋 Input: {actor_input}")
            
            # Exponential backoff: wait 2^attempt seconds before retry
            if attempt > 0:
                wait_time = 2 ** attempt
                print(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Call Apify API with tri_angle/new-fast-airbnb-scraper (correct structure)
                api_payload = {
                    **actor_input,  # Input data
                    "options": {
                        "maxItems": 100,      # CORRECT: maxItems in options!
                        "timeout": 120        # 2 minute timeout
                    }
                }
                
                response = await client.post(
                    "https://api.apify.com/v2/acts/tri_angle~new-fast-airbnb-scraper/run-sync-get-dataset-items",
                    headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
                    json=api_payload
                )
                
                print(f"🔄 HTTP Status: {response.status_code}")
                
                # Check response status
                if response.status_code not in [200, 201]:
                    print(f"❌ API Error {response.status_code}: {response.text[:500]}")
                    if attempt == max_retries - 1:  # Last attempt
                        raise Exception(f"API returned status {response.status_code} after {max_retries} attempts")
                    continue  # Retry
                
                # Parse response
                data = response.json()
                print(f"✅ API Response: {len(data)} Airbnb properties received")
                
                # Debug response structure
                if data and len(data) > 0:
                    first_item = data[0]
                    print(f"🔍 Response structure: {list(first_item.keys())[:8]}...")
                    print(f"🔍 Sample item: {first_item}")
                else:
                    print(f"🔍 Empty response or no data in response")
                    print(f"🔍 Raw response length: {len(data) if data else 'None'}")
                    print(f"🔍 Response type: {type(data)}")
                
                # Parse Airbnb properties from response
                properties = _parse_airbnb_properties(data)
                
                if not properties:
                    print("⚠️ No valid Airbnb properties found in API response")
                    if attempt == max_retries - 1:  # Last attempt
                        return []
                    continue  # Retry
                
                print(f"✅ Successfully parsed {len(properties)} Airbnb properties")
                return properties
                
        except asyncio.TimeoutError:
            print(f"⏰ Request timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise Exception(f"Request timed out after {max_retries} attempts")
                
        except Exception as e:
            print(f"❌ Airbnb API Error (attempt {attempt + 1}): {e}")
            print(f"❌ Error Type: {type(e).__name__}")
            if attempt == max_retries - 1:  # Last attempt
                raise e
    
    return []  # Should not reach here


def _parse_airbnb_properties(data):
    """Parse tri_angle/new-fast-airbnb-scraper response data (new format)"""
    properties = []
    
    try:
        for item in data[:100]:  # Process all properties (max 100 due to scraper limit)
            try:
                # Extract basic info from new format
                name = item.get('name', 'Unknown Property')
                title = item.get('title', '')
                
                # Use title if more descriptive, otherwise use name
                display_name = title if title and len(title) > len(name or '') else name
                
                # Extract price from new pricing object
                pricing_data = item.get('pricing', {})
                price_per_night = 0
                
                if isinstance(pricing_data, dict):
                    # Extract from "€ 558 per night" format
                    price_str = pricing_data.get('price', '€ 0')
                    try:
                        # Remove currency symbols and extract number
                        price_clean = price_str.replace('€', '').replace('$', '').replace(',', '').replace('\xa0', '').strip()
                        price_per_night = float(price_clean) if price_clean else 0
                    except (ValueError, TypeError):
                        price_per_night = 0
                
                # Extract rating from new rating object
                rating_data = item.get('rating', {})
                rating = 4.0  # Default rating
                review_count = 0
                
                if isinstance(rating_data, dict):
                    rating = rating_data.get('average', 4.0)
                    review_count = rating_data.get('reviewsCount', 0)
                
                # Safe conversion
                try:
                    rating = float(rating) if rating is not None else 4.0
                    review_count = int(review_count) if review_count is not None else 0
                except (ValueError, TypeError):
                    rating = 4.0
                    review_count = 0
                
                # Extract property type from roomType
                room_type = item.get('roomType', 'entire_home')
                property_type_map = {
                    'entire_home': 'Entire home',
                    'private_room': 'Private room',
                    'shared_room': 'Shared room',
                    'hotel_room': 'Hotel room'
                }
                property_type = property_type_map.get(room_type, 'Entire home')
                
                # Extract location from coordinates or title
                location = 'City Center'
                if 'coordinates' in item and item['coordinates']:
                    coords = item['coordinates']
                    lat = coords.get('latitude', 0)
                    lon = coords.get('longitude', 0)
                    if lat and lon:
                        location = f"Lat: {lat:.3f}, Lon: {lon:.3f}"
                
                # Extract capacity from subtitles (e.g., "3 queen beds")
                subtitles = item.get('subtitles', [])
                person_capacity = 2  # Default
                
                # Try to extract capacity from subtitles
                for subtitle in subtitles:
                    if 'bed' in subtitle.lower():
                        try:
                            # Extract number from "3 queen beds"
                            import re
                            numbers = re.findall(r'\d+', subtitle)
                            if numbers:
                                person_capacity = int(numbers[0]) * 2  # Assume 2 people per bed
                                break
                        except:
                            pass
                
                # Extract URL
                url = item.get('url', '')
                
                # Extract additional info
                additional_info = item.get('additionalInfo', '')
                badges = item.get('badges', [])
                
                # Create property object matching hotel format for consistency
                property_obj = {
                    'name': str(display_name)[:60] if display_name else 'Unknown Property',
                    'price': int(price_per_night) if price_per_night > 0 else 0,
                    'rating': round(float(rating), 1),
                    'review_count': review_count,
                    'location': location[:50],
                    'property_type': str(property_type)[:30],
                    'person_capacity': min(person_capacity, 12),  # Cap at 12 people
                    'additional_info': additional_info,
                    'badges': badges,
                    'url': str(url)[:300] if url else '',
                    'source': 'Airbnb',
                    'type': 'airbnb',
                    'stars': "⭐" * min(int(rating), 5)
                }
                
                # Only add properties with valid data
                if property_obj['price'] > 0 and property_obj['name'] != 'Unknown Property':
                    properties.append(property_obj)
                    print(f"  🏠 {property_obj['name'][:35]}: {property_obj['price']}€/night ⭐{property_obj['rating']} ({property_obj['property_type']})")
                
            except Exception as e:
                print(f"⚠️ Error parsing Airbnb property: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Airbnb Parser Error: {e}")
    
    # Sort by price-to-rating ratio (best value first)
    if properties:
        properties.sort(key=lambda p: p['price'] / max(p['rating'], 1))
    return properties


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_city_name_from_iata(iata_code):
    """Convert IATA airport codes to city names"""
    cities = {
        'VIE': 'Vienna',
        'BCN': 'Barcelona',
        'FCO': 'Rome',
        'CDG': 'Paris',
        'LHR': 'London',
        'AMS': 'Amsterdam',
        'MUC': 'Munich',
        'ZUR': 'Zurich',
        'BER': 'Berlin',
        'MAD': 'Madrid',
        'LIS': 'Lisbon'
    }
    return cities.get(iata_code.upper(), iata_code)


# =============================================================================
# API HEALTH CHECK
# =============================================================================

async def check_api_health():
    """Check if Apify APIs are accessible"""
    if not APIFY_TOKEN:
        return {"status": "error", "message": "No APIFY_TOKEN configured"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {APIFY_TOKEN}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "status": "healthy",
                    "message": f"Connected as {user_data.get('username', 'Unknown')}",
                    "apis": ["jupri/skyscanner-flight", "voyager/fast-booking-scraper"]
                }
            else:
                return {"status": "error", "message": f"API returned {response.status_code}"}
                
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # Simple test
    async def test_apis():
        print("🧪 Testing Travel APIs...")
        
        # Test flight search
        flights = await search_flights_apify("VIE", "FCO", "2025-08-15")
        print(f"Flight test: {len(flights)} results")
        
        # Test hotel search  
        hotels = await search_hotels_apify("Rome", "2025-08-15", "2025-08-17")
        print(f"Hotel test: {len(hotels)} results")
        
        # Test Airbnb search
        airbnb = await search_airbnb_apify("Rome", "2025-08-15", "2025-08-17", 2)
        print(f"Airbnb test: {len(airbnb)} results")
        
        # Test API health
        health = await check_api_health()
        print(f"API Health: {health}")
    
    asyncio.run(test_apis())