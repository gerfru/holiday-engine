# main.py - Complete FastAPI Application with Live Autocomplete + Crowd-Sourced Features
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, Tuple
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
from services.crowd_sourced_service import SimpleCrowdService, router as crowd_router
from business_logic import TravelCombinationEngine, export_search_results

# Setup logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Holiday Engine",
    description="Intelligent Travel Search & Comparison Platform with Community Tips",
    version="2.1.0",
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
crowd_service = SimpleCrowdService()  # ✅ NEW: Crowd-sourced service

# Include crowd-sourced router
app.include_router(crowd_router, prefix="/api", tags=["crowd-sourced"])  # ✅ NEW

# =============================================================================
# MAIN ROUTES
# =============================================================================

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
            "version": "2.1.0",
            "debug": settings.debug,
            "api_status": api_health["status"],
            "services": {
                "flight_service": "active",
                "accommodation_service": "active", 
                "combination_engine": "active",
                "city_resolver": "active",
                "crowd_service": "active"  # ✅ NEW
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}

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
    Smart travel search with crowd-sourced community tips
    """
    search_start_time = datetime.now()
    
    try:
        # Step 1: Validate and process inputs
        search_params = await _validate_search_params(
            origin, destination, departure, return_date, budget, persons
        )
        
        logger.info(f"Starting smart search: {search_params}")
        
        # Step 2: Resolve cities to IATA codes
        origin_info, dest_info = await _resolve_cities(origin, destination)
        
        # Step 3: Perform all searches concurrently (including crowd tips)
        search_results = await _perform_all_searches(
            origin_info, dest_info, search_params
        )
        
        # Step 4: Create intelligent combinations
        combinations = combination_engine.create_combinations(
            outbound_flights=search_results['flights']['outbound'],
            return_flights=search_results['flights']['return'],
            hotels=search_results['accommodations']['hotels'],
            airbnb_properties=search_results['accommodations']['airbnb'],
            search_params=search_params
        )
        
        # Step 5: Export results (if enabled)
        export_data = None
        if settings.export_csv:
            export_data = await export_search_results(search_results, search_params)
        
        # Step 6: Calculate search time
        search_time = (datetime.now() - search_start_time).total_seconds()
        
        # Step 7: Render results with crowd-sourced tips
        return templates.TemplateResponse("results.html", {
            "request": request,
            "combinations": combinations,
            "outbound_flights": search_results['flights']['outbound'],
            "return_flights": search_results['flights']['return'],
            "hotels": search_results['accommodations']['hotels'],
            "airbnb_properties": search_results['accommodations']['airbnb'],
            "crowd_tips": search_results['crowd_tips'],  # ✅ NEW: Community tips
            "origin": f"{origin_info['city']} ({origin_info['iata']})",
            "destination": f"{dest_info['city']} ({dest_info['iata']})",
            "origin_iata": origin_info['iata'],
            "dest_iata": dest_info['iata'],
            "destination_city": dest_info['city'],  # ✅ NEW: For crowd tips
            "departure": search_params['departure'],
            "return_date": search_params['return_date'],
            "checkin": search_params['departure'],
            "checkout": search_params['return_date'],
            "nights": search_params['nights'],
            "budget": search_params['budget'],
            "persons": search_params['persons'],
            "search_time": round(search_time, 2),
            "export_data": export_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "error_type": "validation"
        })
        
    except ApiClientError as e:
        logger.error(f"API error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Search service temporarily unavailable. Please try again later.",
            "error_type": "api"
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in smart search: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "An unexpected error occurred. Please try again.",
            "error_type": "system"
        })

# =============================================================================
# API ROUTES
# =============================================================================

@app.get("/api/cities/autocomplete")
async def city_autocomplete(q: str = ""):
    """
    Live city autocomplete using OpenStreetMap Nominatim
    Enhanced with better filtering and performance
    """
    if not q or len(q) < 2:
        return {"suggestions": []}
    
    try:
        logger.info(f"Autocomplete search: '{q}'")
        
        # Call Nominatim API with optimized parameters
        suggestions = await _fetch_city_suggestions(q)
        
        logger.info(f"Found {len(suggestions)} city suggestions for '{q}'")
        return {"suggestions": suggestions}
    
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
    """
    if not city:
        return {"error": "City name required"}
    
    try:
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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _validate_search_params(
    origin: str, 
    destination: str, 
    departure: str, 
    return_date: str, 
    budget: Optional[str], 
    persons: int
) -> Dict[str, Any]:
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

async def _resolve_cities(origin: str, destination: str) -> Tuple[Dict[str, str], Dict[str, str]]:
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

async def _perform_all_searches(
    origin_info: Dict[str, str], 
    dest_info: Dict[str, str], 
    search_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Perform all searches concurrently: flights, accommodations, and crowd tips
    """
    
    logger.info("Starting concurrent search for flights, accommodations, and community tips")
    
    # Create all search tasks
    flight_task = flight_service.search_round_trip(
        origin=origin_info['iata'],
        destination=dest_info['iata'],
        departure_date=search_params['departure'],
        return_date=search_params['return_date'],
        max_results_per_direction=settings.max_flights_per_search // 2
    )
    
    accommodation_task = accommodation_service.search_all_accommodations(
        city=search_params['destination'],
        checkin=search_params['departure'],
        checkout=search_params['return_date'],
        guests=search_params['persons'],
        max_hotels=settings.max_hotels_per_search,
        max_airbnb=settings.max_airbnb_per_search
    )
    
    # ✅ NEW: Community tips task
    crowd_tips_task = crowd_service.get_travel_tips(dest_info['city'])
    
    # Execute all tasks concurrently
    try:
        flights, accommodations, crowd_tips = await asyncio.gather(
            flight_task,
            accommodation_task,
            crowd_tips_task,
            return_exceptions=True
        )
        
        # Handle exceptions for each service
        if isinstance(flights, Exception):
            logger.error(f"Flight search failed: {flights}")
            flights = {'outbound': [], 'return': []}
        
        if isinstance(accommodations, Exception):
            logger.error(f"Accommodation search failed: {accommodations}")
            accommodations = {'hotels': [], 'airbnb': []}
        
        if isinstance(crowd_tips, Exception):
            logger.error(f"Crowd tips search failed: {crowd_tips}")
            crowd_tips = []
        
        # Validate core results (flights and accommodations)
        total_flights = len(flights['outbound']) + len(flights['return'])
        total_accommodations = len(accommodations['hotels']) + len(accommodations['airbnb'])
        
        if total_flights == 0:
            raise ValidationError(f"No flights found for {origin_info['city']} ↔ {dest_info['city']} on selected dates")
        
        if total_accommodations == 0:
            raise ValidationError(f"No accommodations found in {dest_info['city']} for selected dates")
        
        logger.info(f"Search completed: {total_flights} flights, {total_accommodations} accommodations, {len(crowd_tips)} community tips")
        
        return {
            'flights': flights,
            'accommodations': accommodations,
            'crowd_tips': crowd_tips  # ✅ NEW: Include community tips
        }
        
    except Exception as e:
        logger.error(f"Concurrent search failed: {e}")
        raise

async def _fetch_city_suggestions(query: str) -> list:
    """
    Fetch city suggestions from OpenStreetMap Nominatim
    Optimized and refactored for better maintainability
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "addressdetails": 1,
        "limit": 8,
        "accept-language": "de,en",
        "featuretype": "city"
    }
    
    headers = {
        "User-Agent": "HolidayEngine/2.1 (travel-search-platform)"
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"Nominatim API error: {response.status_code}")
            return []
        
        data = response.json()
        
        # Debug logging
        logger.info(f"DEBUG: Raw Nominatim data for '{query}':")
        for i, item in enumerate(data[:3]):
            logger.info(f"  Result {i}: type='{item.get('type')}', class='{item.get('class')}', name='{item.get('name')}'")
        
        return _process_city_suggestions(data)

def _process_city_suggestions(data: list) -> list:
    """Process raw Nominatim data into clean city suggestions"""
    suggestions = []
    seen_cities = set()
    
    # Valid place types for cities
    valid_types = [
        "city", "town", "village", "municipality",
        "administrative", "hamlet", "suburb", "quarter", "neighbourhood"
    ]
    valid_classes = ["place", "boundary"]
    
    for item in data:
        place_type = item.get("type", "")
        place_class = item.get("class", "")
        
        # Filter by valid types/classes
        if place_type not in valid_types and place_class not in valid_classes:
            continue
        
        # Extract city information
        address = item.get("address", {})
        city_name = (
            address.get("city") or 
            address.get("town") or 
            address.get("village") or
            address.get("municipality") or
            address.get("hamlet") or
            item.get("name", "")
        )
        
        # Skip duplicates and empty names
        if not city_name or city_name.lower() in seen_cities:
            continue
        
        seen_cities.add(city_name.lower())
        
        # Build suggestion
        country = address.get("country", "")
        country_code = address.get("country_code", "").upper()
        
        suggestion = {
            "city": city_name,
            "country": country,
            "country_code": country_code,
            "display_name": f"{city_name}, {country}" if country else city_name,
            "lat": float(item.get("lat", 0)),
            "lon": float(item.get("lon", 0)),
            "importance": item.get("importance", 0),
            "type": place_type
        }
        
        suggestions.append(suggestion)
    
    # Sort by importance and return top results
    suggestions.sort(key=lambda x: x["importance"], reverse=True)
    return suggestions[:6]

# =============================================================================
# TEST ENDPOINTS
# =============================================================================

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

@app.post("/test-crowd-tips")  # ✅ NEW: Test endpoint for crowd tips
async def test_crowd_tips(
    destination: str = Form("Barcelona")
):
    """Test crowd-sourced tips endpoint"""
    try:
        tips = await crowd_service.get_travel_tips(destination)
        return {
            "success": True,
            "query": {"destination": destination},
            "results": tips,
            "count": len(tips)
        }
    except Exception as e:
        logger.error(f"Crowd tips test failed: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# EXCEPTION CLASSES
# =============================================================================

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

# =============================================================================
# STARTUP/SHUTDOWN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("Starting Holiday Engine v2.1 with Community Tips")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"API token configured: {'Yes' if settings.apify_token else 'No'}")
    
    # Test API connectivity
    try:
        health = await api_client.health_check()
        logger.info(f"API health check: {health['status']}")
    except Exception as e:
        logger.warning(f"API health check failed: {e}")
    
    # Test crowd service
    try:
        test_tips = await crowd_service.get_travel_tips("Barcelona")
        logger.info(f"Crowd service test: {len(test_tips)} tips loaded")
    except Exception as e:
        logger.warning(f"Crowd service test failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Shutting down Holiday Engine v2.1")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting Holiday Engine v2.1 with Community Tips...")
    logger.info(f"🌐 Open: http://{settings.host}:{settings.port}")
    logger.info(f"🔧 Health: http://{settings.host}:{settings.port}/health")
    logger.info(f"📚 API Docs: http://{settings.host}:{settings.port}/docs")
    logger.info(f"🌍 Community Tips: Integrated!")
    
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        reload=settings.debug
    )