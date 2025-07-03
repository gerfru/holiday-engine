# main.py - Complete FastAPI Application with Live Autocomplete
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import asyncio
import logging
import httpx
from datetime import datetime

# Import refactored services
from config.settings import settings
from utils.api_client import create_apify_client, ApiClientError
from services.flight_service import FlightService
from services.hotel_service import AccommodationService
from services.city_resolver import CityResolverService
from business_logic import TravelCombinationEngine, export_search_results

# Setup
logger = logging.getLogger(__name__)
app = FastAPI(
    title="Holiday Engine",
    description="Intelligent Travel Search & Comparison Platform",
    version="2.0.0",
    debug=settings.debug
)

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize services
api_client = create_apify_client(
    api_token=settings.apify_token,
    max_retries=settings.max_retries,
    base_delay=settings.base_retry_delay,
    max_delay=settings.max_retry_delay,
    timeout=settings.api_timeout
)

flight_service = FlightService(api_client)
accommodation_service = AccommodationService(api_client)
combination_engine = TravelCombinationEngine()
city_resolver = CityResolverService()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main search page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Application health check"""
    try:
        api_health = await api_client.health_check()
        return {
            "status": "healthy",
            "version": "2.0.0",
            "debug": settings.debug,
            "api_status": api_health["status"],
            "services": {
                "flight_service": "active",
                "accommodation_service": "active", 
                "combination_engine": "active",
                "city_resolver": "active"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Live Autocomplete APIs
@app.get("/api/cities/autocomplete")
async def city_autocomplete(q: str = ""):
    """
    Live city autocomplete using OpenStreetMap Nominatim
    
    Args:
        q: Query string (e.g., "Mala" for "Malaga")
        
    Returns:
        List of city suggestions with coordinates
    """
    if not q or len(q) < 2:
        return {"suggestions": []}
    
    try:
        logger.info(f"Autocomplete search: '{q}'")
        
        # Call Nominatim API
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": q,
            "format": "json",
            "addressdetails": 1,
            "limit": 8,  # More results for better selection
            "accept-language": "de,en",  # Prefer German, fallback English
            "featuretype": "city"  # Focus on cities
        }
        
        headers = {
            "User-Agent": "HolidayEngine/2.0 (travel-search-platform)"
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                logger.info(f"DEBUG: Raw Nominatim data for '{q}':")
                for i, item in enumerate(data[:3]):  # Erste 3 Ergebnisse
                    logger.info(f"  Result {i}: type='{item.get('type')}', class='{item.get('class')}', name='{item.get('name')}'")

                # Filter and format results
                suggestions = []
                seen_cities = set()  # Avoid duplicates
                
                for item in data:
                    # Extract city information
                    display_name = item.get("display_name", "")
                    place_type = item.get("type", "")
                    place_class = item.get("class", "")
                    
                    # EXPANDED: Include more place types
                    valid_types = [
                        "city", "town", "village", "municipality",
                        "administrative",  # ✅ For places like Schladming
                        "hamlet", "suburb", "quarter", "neighbourhood"
                    ]
                    
                    # Also check if it's a place class (boundary, place, etc.)
                    valid_classes = ["place", "boundary"]
                    
                    # Include if type OR class is valid
                    if place_type not in valid_types and place_class not in valid_classes:
                        continue
                    
                    # Extract clean city name from address
                    address = item.get("address", {})
                    city_name = (
                        address.get("city") or 
                        address.get("town") or 
                        address.get("village") or
                        address.get("municipality") or
                        address.get("hamlet") or  # ✅ Small places
                        item.get("name", "")
                    )
                    
                    if not city_name or city_name.lower() in seen_cities:
                        continue
                    
                    seen_cities.add(city_name.lower())
                    
                    # Get country for context
                    country = address.get("country", "")
                    country_code = address.get("country_code", "").upper()
                    
                    # Create suggestion
                    suggestion = {
                        "city": city_name,
                        "country": country,
                        "country_code": country_code,
                        "display_name": f"{city_name}, {country}" if country else city_name,
                        "lat": float(item.get("lat", 0)),
                        "lon": float(item.get("lon", 0)),
                        "importance": item.get("importance", 0),  # OSM importance score
                        "type": place_type
                    }
                    
                    suggestions.append(suggestion)
                
                # Sort by importance (OSM's relevance score)
                suggestions.sort(key=lambda x: x["importance"], reverse=True)
                
                logger.info(f"Found {len(suggestions)} city suggestions for '{q}'")
                return {"suggestions": suggestions[:6]}  # Return top 6
            
            else:
                logger.warning(f"Nominatim API error: {response.status_code}")
                return {"suggestions": [], "error": "Search service unavailable"}
        
    except asyncio.TimeoutError:
        logger.warning(f"Autocomplete timeout for query: '{q}'")
        return {"suggestions": [], "error": "Search timeout"}
        
    except Exception as e:
        logger.error(f"Autocomplete error for '{q}': {e}")
        return {"suggestions": [], "error": "Search failed"}

@app.get("/api/cities/resolve")
async def resolve_city_to_airport(city: str = ""):
    """
    Resolve a city name to nearest airport IATA code
    
    Args:
        city: City name to resolve
        
    Returns:
        Airport information or error
    """
    if not city:
        return {"error": "City name required"}
    
    try:
        # Use your existing city resolver
        iata, resolved_city, suggestions = await city_resolver.resolve_to_iata(city)
        
        if iata:
            return {
                "success": True,
                "iata": iata,
                "city": resolved_city,
                "original_query": city
            }
        else:
            return {
                "success": False,
                "error": f"Could not find airport for '{city}'",
                "suggestions": suggestions,
                "original_query": city
            }
    
    except Exception as e:
        logger.error(f"City resolution error: {e}")
        return {"error": "Resolution failed"}

@app.post("/smart-search")
async def smart_search(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    departure: str = Form(...),
    return_date: str = Form(...),
    budget: Optional[str] = Form(None),
    persons: int = Form(2)
):
    """
    Smart travel search with improved error handling and structure
    """
    try:
        # Validate and process inputs
        search_params = await _validate_search_params(
            origin, destination, departure, return_date, budget, persons
        )
        
        logger.info(f"Starting smart search: {search_params}")
        
        # Step 1: Resolve cities to IATA codes
        origin_info, dest_info = await _resolve_cities(origin, destination)
        
        # Step 2: Search flights and accommodations concurrently
        search_results = await _perform_concurrent_search(
            origin_info, dest_info, search_params
        )
        
        # Step 3: Create intelligent combinations
        combinations = combination_engine.create_combinations(
            outbound_flights=search_results['flights']['outbound'],
            return_flights=search_results['flights']['return'],
            hotels=search_results['accommodations']['hotels'],
            airbnb_properties=search_results['accommodations']['airbnb'],
            search_params=search_params
        )
        
        # Step 4: Export results (if enabled)
        if settings.export_csv:
            await export_search_results(search_results, search_params)
        
        # Step 5: Render results
        return templates.TemplateResponse("results.html", {
            "request": request,
            "combinations": combinations,
            "outbound_flights": search_results['flights']['outbound'],
            "return_flights": search_results['flights']['return'],
            "hotels": search_results['accommodations']['hotels'],
            "airbnb_properties": search_results['accommodations']['airbnb'],
            "origin": f"{origin_info['city']} ({origin_info['iata']})",
            "destination": f"{dest_info['city']} ({dest_info['iata']})",
            "origin_iata": origin_info['iata'],
            "dest_iata": dest_info['iata'],
            "departure": search_params['departure'],
            "return_date": search_params['return_date'],
            "checkin": search_params['departure'],
            "checkout": search_params['return_date'],
            "nights": search_params['nights'],
            "budget": search_params['budget'],
            "persons": search_params['persons']
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })
        
    except ApiClientError as e:
        logger.error(f"API error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Search service temporarily unavailable. Please try again later."
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in smart search: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again."
        })

# Helper functions
async def _validate_search_params(
    origin: str, 
    destination: str, 
    departure: str, 
    return_date: str, 
    budget: Optional[str], 
    persons: int
) -> dict:
    """Validate and process search parameters"""
    
    # Validate persons
    if not 1 <= persons <= 10:
        raise ValidationError("Number of persons must be between 1 and 10")
    
    # Validate dates
    try:
        departure_date = datetime.strptime(departure, '%Y-%m-%d').date()
        return_date_obj = datetime.strptime(return_date, '%Y-%m-%d').date()
        
        if departure_date >= return_date_obj:
            raise ValidationError("Return date must be after departure date")
        
        if departure_date < datetime.now().date():
            raise ValidationError("Departure date must be in the future")
        
        nights = (return_date_obj - departure_date).days
        if nights > 30:
            raise ValidationError("Maximum trip duration is 30 days")
            
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    # Process budget
    budget_int = None
    if budget and budget.strip():
        try:
            budget_int = int(budget)
            if budget_int < 50:
                raise ValidationError("Budget must be at least €50")
        except ValueError:
            raise ValidationError("Budget must be a valid number")
    
    return {
        'origin': origin.strip(),
        'destination': destination.strip(),
        'departure': departure,
        'return_date': return_date,
        'budget': budget_int,
        'persons': persons,
        'nights': nights
    }

async def _resolve_cities(origin: str, destination: str) -> tuple:
    """Resolve city names to IATA codes"""
    
    logger.info(f"Resolving cities: {origin} → {destination}")
    
    # Resolve origin
    origin_iata, origin_city, origin_suggestions = await city_resolver.resolve_to_iata(origin)
    if not origin_iata:
        suggestions_text = ', '.join(origin_suggestions[:3]) if origin_suggestions else 'None'
        raise ValidationError(f"Origin city '{origin}' not found. Suggestions: {suggestions_text}")
    
    # Resolve destination  
    dest_iata, dest_city, dest_suggestions = await city_resolver.resolve_to_iata(destination)
    if not dest_iata:
        suggestions_text = ', '.join(dest_suggestions[:3]) if dest_suggestions else 'None'
        raise ValidationError(f"Destination city '{destination}' not found. Suggestions: {suggestions_text}")
    
    if origin_iata == dest_iata:
        raise ValidationError("Origin and destination cannot be the same")
    
    logger.info(f"Resolved: {origin} → {origin_iata}, {destination} → {dest_iata}")
    
    return (
        {'iata': origin_iata, 'city': origin_city},
        {'iata': dest_iata, 'city': dest_city}
    )

async def _perform_concurrent_search(origin_info: dict, dest_info: dict, search_params: dict) -> dict:
    """Perform all searches concurrently"""
    
    logger.info("Starting concurrent search for flights and accommodations")
    
    # Create search tasks
    flight_task = flight_service.search_round_trip(
        origin=origin_info['iata'],
        destination=dest_info['iata'],
        departure_date=search_params['departure'],
        return_date=search_params['return_date'],
        max_results_per_direction=settings.max_flights_per_search // 2
    )
    
    accommodation_task = accommodation_service.search_all_accommodations(
        city=search_params['destination'],  # ✅ Use original destination for hotels!
        checkin=search_params['departure'],
        checkout=search_params['return_date'],
        guests=search_params['persons'],
        max_hotels=settings.max_hotels_per_search,
        max_airbnb=settings.max_airbnb_per_search
    )
    
    # Execute concurrently
    try:
        flights, accommodations = await asyncio.gather(
            flight_task,
            accommodation_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(flights, Exception):
            logger.error(f"Flight search failed: {flights}")
            flights = {'outbound': [], 'return': []}
        
        if isinstance(accommodations, Exception):
            logger.error(f"Accommodation search failed: {accommodations}")
            accommodations = {'hotels': [], 'airbnb': []}
        
        # Validate we have some results
        total_flights = len(flights['outbound']) + len(flights['return'])
        total_accommodations = len(accommodations['hotels']) + len(accommodations['airbnb'])
        
        if total_flights == 0:
            raise ValidationError(f"No flights found for {origin_info['city']} ↔ {dest_info['city']} on selected dates")
        
        if total_accommodations == 0:
            raise ValidationError(f"No accommodations found in {dest_info['city']} for selected dates")
        
        logger.info(f"Search completed: {total_flights} flights, {total_accommodations} accommodations")
        
        return {
            'flights': flights,
            'accommodations': accommodations
        }
        
    except Exception as e:
        logger.error(f"Concurrent search failed: {e}")
        raise

# Test endpoints
@app.post("/test-flights")
async def test_flights(
    origin: str = Form("VIE"),
    destination: str = Form("BCN"),
    date: str = Form("2025-08-15")
):
    """Simple flight test endpoint"""
    try:
        flights = await flight_service.search_flights(origin, destination, date, 5)
        return {
            "success": True,
            "query": {"origin": origin, "destination": destination, "date": date},
            "results": flights,
            "count": len(flights)
        }
    except Exception as e:
        logger.error(f"Flight test failed: {e}")
        return {"success": False, "error": str(e)}

@app.post("/test-hotels")
async def test_hotels(
    city: str = Form("Barcelona"),
    checkin: str = Form("2025-08-15"),
    checkout: str = Form("2025-08-17")
):
    """Simple hotel test endpoint"""
    try:
        hotels = await accommodation_service.search_hotels(city, checkin, checkout, 10)
        return {
            "success": True,
            "query": {"city": city, "checkin": checkin, "checkout": checkout},
            "results": hotels,
            "count": len(hotels)
        }
    except Exception as e:
        logger.error(f"Hotel test failed: {e}")
        return {"success": False, "error": str(e)}

# Custom exceptions
class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Holiday Engine v2.0")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API token configured: {'Yes' if settings.apify_token else 'No'}")
    
    # Test API connectivity
    try:
        health = await api_client.health_check()
        logger.info(f"API health check: {health['status']}")
    except Exception as e:
        logger.warning(f"API health check failed: {e}")

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Holiday Engine v2.0...")
    logger.info(f"🌐 Open: http://{settings.host}:{settings.port}")
    logger.info(f"🔧 Health: http://{settings.host}:{settings.port}/health")
    
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        reload=settings.debug
    )