# travel_api.py - Clean, Robust & Functional Travel APIs
import asyncio
import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# =============================================================================
# FLIGHT SEARCH - jupri/skyscanner-flight Actor
# =============================================================================

async def search_flights_apify(origin: str, destination: str, date: str):
    """
    Search flights using jupri/skyscanner-flight Apify Actor
    
    Args:
        origin (str): IATA airport code (e.g., 'VIE')
        destination (str): IATA airport code (e.g., 'FCO') 
        date (str): Departure date in YYYY-MM-DD format
        
    Returns:
        list: List of flight dictionaries with airline, price, time, duration
    """
    print(f"🔍 APIFY FLIGHTS: {origin} → {destination} on {date}")
    
    # Check API token
    if not APIFY_TOKEN:
        print("❌ No APIFY_TOKEN found, using mock data")
        return await _mock_flight_search(origin, destination, date)
    
    # Prepare actor input (jupri/skyscanner-flight format)
    actor_input = {
        "origin.0": origin.upper(),
        "target.0": destination.upper(),
        "depart.0": date,
        "market": "DE",
        "currency": "EUR"
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"📡 Starting jupri/skyscanner-flight actor...")
            print(f"📋 Input: {actor_input}")
            
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
                return await _mock_flight_search(origin, destination, date)
            
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
                print("⚠️ No valid flights found, falling back to mock")
                return await _mock_flight_search(origin, destination, date)
            
            print(f"✅ Successfully parsed {len(flights)} flights")
            return flights
            
    except Exception as e:
        print(f"❌ Flight API Error: {e}")
        print(f"❌ Error Type: {type(e).__name__}")
        return await _mock_flight_search(origin, destination, date)


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
        
        flight = {
            'airline': airline,
            'price': int(price) if price else 0,
            'time': formatted_time,
            'duration': formatted_duration + stops_text,
            'stops': stop_count,
            'source': 'Skyscanner'
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


async def _mock_flight_search(origin: str, destination: str, date: str):
    """Mock flight data for testing/fallback"""
    print(f"🔄 MOCK: Flights {origin} → {destination}")
    await asyncio.sleep(0.5)  # Simulate API delay
    
    return [
        {"airline": "Lufthansa", "price": 299, "time": "08:30", "duration": "3h 15m (nonstop)", "stops": 0, "source": "Mock"},
        {"airline": "Austrian Airlines", "price": 259, "time": "14:20", "duration": "3h 30m (nonstop)", "stops": 0, "source": "Mock"},
        {"airline": "Eurowings", "price": 199, "time": "06:45", "duration": "3h 20m (nonstop)", "stops": 0, "source": "Mock"}
    ]


# =============================================================================
# HOTEL SEARCH - voyager/booking-scraper Actor  
# =============================================================================

async def search_hotels_apify(city: str, checkin: str, checkout: str):
    """
    Search hotels using voyager/booking-scraper Apify Actor
    
    Args:
        city (str): City name (e.g., 'Barcelona')
        checkin (str): Check-in date in YYYY-MM-DD format
        checkout (str): Check-out date in YYYY-MM-DD format
        
    Returns:
        list: List of hotel dictionaries with name, price, rating, location
    """
    print(f"🏨 APIFY HOTELS: {city} ({checkin} - {checkout})")
    
    # Check API token
    if not APIFY_TOKEN:
        print("❌ No APIFY_TOKEN found, using mock data")
        return await _mock_hotel_search(city, checkin, checkout)
    
    # Prepare actor input (voyager/booking-scraper format)
    actor_input = {
        "currency": "EUR",
        "language": "de",
        "maxItems": 20,
        "minMaxPrice": "0-999999",
        "search": city,
        "sortBy": "price",
        "starsCountFilter": "any",
        "checkIn": checkin,
        "checkOut": checkout,
        "rooms": 1,
        "adults": 2,
        "children": 0
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"📡 Starting voyager/booking-scraper actor...")
            print(f"📋 Input: {actor_input}")
            
            # Call Apify API
            response = await client.post(
                "https://api.apify.com/v2/acts/voyager~booking-scraper/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
                json=actor_input
            )
            
            print(f"🔄 HTTP Status: {response.status_code}")
            
            # Check response status
            if response.status_code not in [200, 201]:
                print(f"❌ API Error {response.status_code}: {response.text[:500]}")
                return await _mock_hotel_search(city, checkin, checkout)
            
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
                print("⚠️ No valid hotels found, falling back to mock")
                return await _mock_hotel_search(city, checkin, checkout)
            
            print(f"✅ Successfully parsed {len(hotels)} hotels")
            return hotels
            
    except Exception as e:
        print(f"❌ Hotel API Error: {e}")
        print(f"❌ Error Type: {type(e).__name__}")
        return await _mock_hotel_search(city, checkin, checkout)


def _parse_booking_hotels(data):
    """Parse voyager/booking-scraper response data"""
    hotels = []
    
    try:
        for item in data[:10]:  # Limit to 10 hotels
            try:
                # Extract basic info
                name = item.get('name', 'Unknown Hotel')
                price = item.get('price', 0)
                rating = item.get('rating', 0)
                stars = item.get('stars', 0)
                
                # Extract location
                address = item.get('address', {})
                location = address.get('full', address.get('city', 'Unknown'))
                
                # Extract property type
                property_type = item.get('type', 'hotel')
                
                # Extract URL
                url = item.get('url', '')
                
                # Calculate final rating
                final_rating = rating if rating > 0 else (stars if stars > 0 else 4.0)
                
                # Check for room prices if main price is 0
                if price <= 0 and 'rooms' in item and item['rooms']:
                    room_prices = []
                    for room in item['rooms']:
                        if 'options' in room:
                            for option in room['options']:
                                room_price = option.get('price', 0)
                                if room_price > 0:
                                    room_prices.append(room_price)
                    if room_prices:
                        price = min(room_prices)  # Cheapest room price
                
                # Create hotel object
                hotel = {
                    'name': str(name)[:60],
                    'price': int(price) if price > 0 else 0,
                    'rating': round(float(final_rating), 1),
                    'location': str(location)[:50] if location else "City Center",
                    'stars': "⭐" * min(int(final_rating), 5),
                    'url': url[:100] if url else '',
                    'type': property_type,
                    'source': 'Booking.com'
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
    hotels.sort(key=lambda h: h['price'] / max(h['rating'], 1))
    return hotels


async def _mock_hotel_search(city: str, checkin: str, checkout: str):
    """Mock hotel data for testing/fallback"""
    print(f"🔄 MOCK: Hotels in {city}")
    await asyncio.sleep(0.3)  # Simulate API delay
    
    # City-specific mock data
    city_hotels = {
        'Barcelona': [
            {"name": "Hotel Arts Barcelona", "price": 450, "rating": 4.8, "location": "Port Olympic"},
            {"name": "Casa Milà Suites", "price": 280, "rating": 4.5, "location": "Eixample"},
            {"name": "Generator Barcelona", "price": 89, "rating": 4.1, "location": "Gràcia"}
        ],
        'Rome': [
            {"name": "Hotel de Russie", "price": 520, "rating": 4.9, "location": "Via del Corso"},
            {"name": "The First Roma Dolce", "price": 180, "rating": 4.3, "location": "Termini"},
            {"name": "Rome Times Hotel", "price": 95, "rating": 3.9, "location": "Esquilino"}
        ],
        'Paris': [
            {"name": "Le Meurice", "price": 680, "rating": 4.9, "location": "1st Arrondissement"},
            {"name": "Hotel Malte Opera", "price": 220, "rating": 4.4, "location": "2nd Arrondissement"},
            {"name": "MIJE Hostel", "price": 65, "rating": 3.8, "location": "Marais"}
        ]
    }
    
    # Default hotels for unknown cities
    default_hotels = [
        {"name": "City Center Hotel", "price": 180, "rating": 4.2, "location": "City Center"},
        {"name": "Budget Inn", "price": 89, "rating": 3.8, "location": "Outskirts"},
        {"name": "Luxury Resort", "price": 350, "rating": 4.7, "location": "Premium District"}
    ]
    
    hotels = city_hotels.get(city, default_hotels)
    
    # Add stars and source
    for hotel in hotels:
        hotel["stars"] = "⭐" * int(hotel["rating"])
        hotel["source"] = "Mock"
        hotel["type"] = "hotel"
        hotel["url"] = ""
    
    return hotels


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
                    "apis": ["jupri/skyscanner-flight", "voyager/booking-scraper"]
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
        
        # Test API health
        health = await check_api_health()
        print(f"API Health: {health}")
    
    asyncio.run(test_apis())