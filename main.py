# main.py - Clean FastAPI Travel App
from fastapi import FastAPI, Request, Form
from typing import Optional
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import csv
import json
from datetime import datetime, timedelta

# Import APIs and simplified city resolver
from travel_api import search_flights_apify, search_hotels_apify, search_airbnb_apify
from smart_city_lookup_simple import hybrid_city_to_iata
from smart_search_with_progress import smart_search_with_progress

# FastAPI Setup
app = FastAPI(title="Travel Comparison Platform")

# Templates setup
templates = Jinja2Templates(directory="templates")

# Global progress tracking
search_progress = {}
search_results = {}  # Store search results by search_id

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "travel-platform"}

# Main page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Hauptseite - lädt HTML Template"""
    return templates.TemplateResponse("index.html", {"request": request})

# Progress tracking functions
def update_search_progress(search_id: str, step: str, message: str = None, progress: int = None, results: dict = None, redirect_url: str = None):
    """Update search progress for a given search ID"""
    if search_id not in search_progress:
        search_progress[search_id] = {"status": "started", "step": "initialized"}
    
    search_progress[search_id].update({
        "step": step,
        "message": message,
        "progress": progress,
        "results": results,
        "redirect_url": redirect_url,
        "timestamp": datetime.now().isoformat()
    })

async def generate_progress_stream(search_id: str):
    """Generate Server-Sent Events stream for search progress"""
    while search_id not in search_progress:
        await asyncio.sleep(0.1)
    
    last_update = None
    while True:
        current_progress = search_progress.get(search_id, {})
        
        # Only send update if something changed
        if current_progress != last_update:
            data = json.dumps(current_progress)
            yield f"data: {data}\n\n"
            last_update = current_progress.copy()
            
            # Stop streaming if search is completed
            if current_progress.get("redirect_url"):
                break
        
        await asyncio.sleep(0.5)  # Check every 500ms

@app.get("/search-progress/{search_id}")
async def search_progress_stream(search_id: str):
    """Server-Sent Events endpoint for search progress"""
    return StreamingResponse(
        generate_progress_stream(search_id),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.get("/search-with-progress", response_class=HTMLResponse)
async def search_with_progress_page(request: Request, search_id: str = None):
    """Show search progress page"""
    return templates.TemplateResponse("search_with_progress.html", {
        "request": request,
        "search_id": search_id
    })

@app.post("/search-with-progress")
async def start_search_with_progress(
    request: Request,
    origin: str = Form(...),
    destination: str = Form(...),
    departure: str = Form(...),
    return_date: str = Form(...),
    budget: Optional[str] = Form(None),
    persons: int = Form(2)
):
    """Start search with progress tracking"""
    import uuid
    search_id = str(uuid.uuid4())[:8]
    
    # Create progress callback
    def progress_callback(step: str, message: str = None, progress: int = None, results: dict = None):
        update_search_progress(search_id, step, message, progress, results)
    
    # Start background search task
    async def background_search():
        try:
            result = await smart_search_with_progress(
                origin, destination, departure, return_date, budget, persons, progress_callback
            )
            
            if result.get('success'):
                # Store results
                search_results[search_id] = result['results']
                # Set redirect URL to results page
                update_search_progress(
                    search_id, 'completed', 'Suche abgeschlossen!', 100, 
                    result['summary'], f'/results/{search_id}'
                )
            else:
                # Handle error
                update_search_progress(
                    search_id, 'error', f"Fehler: {result.get('error', 'Unbekannter Fehler')}", 0
                )
        
        except Exception as e:
            update_search_progress(
                search_id, 'error', f"Fehler: {str(e)[:50]}...", 0
            )
    
    # Start background task
    asyncio.create_task(background_search())
    
    # Redirect to progress page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/search-with-progress?search_id={search_id}", status_code=302)

# Simple flight search (for testing)
@app.post("/test-flights")
async def test_flights(
    origin: str = Form("VIE"),
    destination: str = Form("BCN"), 
    date: str = Form("2025-08-15")
):
    """Simple test endpoint"""
    try:
        print(f"🔍 Testing: {origin} → {destination} on {date}")
        flights = await search_flights_apify(origin, destination, date)
        print(f"✅ Found {len(flights)} flights")
        
        return {
            "success": True,
            "query": {"origin": origin, "destination": destination, "date": date},
            "results": flights,
            "count": len(flights)
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}

# Smart search - the main feature
@app.post("/smart-search")
async def smart_search(
    request: Request,  # ← Fix: Add missing request parameter
    origin: str = Form(...),
    destination: str = Form(...),
    departure: str = Form(...),
    return_date: str = Form(...),
    budget: Optional[str] = Form(None),
    persons: int = Form(2)
):
    """Smart travel search with combinations"""
    try:
        # Convert budget to integer if provided
        budget_int = None
        if budget and budget.strip():
            try:
                budget_int = int(budget)
            except ValueError:
                budget_int = None
        
        print(f"🧠 Smart Search: {origin}→{destination}, {persons} persons, budget: {budget_int}")
        
        # Step 0: Resolve city names to IATA codes (using simplified resolver)
        print(f"🔍 Resolving origin city: {origin}")
        origin_iata, origin_city, origin_suggestions = await hybrid_city_to_iata(origin)
        if not origin_iata:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Origin city '{origin}' not found. Suggestions: {', '.join(origin_suggestions[:3]) if origin_suggestions else 'None'}"
            })
        
        print(f"🔍 Resolving destination city: {destination}")
        dest_iata, dest_city, dest_suggestions = await hybrid_city_to_iata(destination)
        if not dest_iata:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Destination city '{destination}' not found. Suggestions: {', '.join(dest_suggestions[:3]) if dest_suggestions else 'None'}"
            })
        
        print(f"✅ Resolved: {origin} → {origin_iata}, {destination} → {dest_iata}")
        
        # Step 1: Search flights
        print("📡 Searching outbound flights...")
        try:
            outbound_flights = await search_flights_apify(origin_iata, dest_iata, departure)
            print(f"✅ Found {len(outbound_flights)} outbound flights")
        except Exception as e:
            print(f"❌ Failed to fetch outbound flights: {e}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Flight search failed: Unable to find flights from {origin_city} to {dest_city}. Please try again later or contact support."
            })
        
        print("📡 Searching return flights...")
        try:
            return_flights = await search_flights_apify(dest_iata, origin_iata, return_date)
            print(f"✅ Found {len(return_flights)} return flights")
        except Exception as e:
            print(f"❌ Failed to fetch return flights: {e}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Flight search failed: Unable to find return flights from {dest_city} to {origin_city}. Please try again later or contact support."
            })
        
        # Step 2: Search hotels
        city = dest_city  # Use resolved city name
        print(f"📡 Searching hotels in {city}...")
        try:
            hotels = await search_hotels_apify(city, departure, return_date)
            print(f"✅ Found {len(hotels)} hotels")
        except Exception as e:
            print(f"❌ Failed to fetch hotels: {e}")
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"Hotel search failed: Unable to find hotels in {city}. Please try again later or contact support."
            })
        
        # Step 3: Search Airbnb properties
        print(f"📡 Searching Airbnb properties in {city}...")
        try:
            airbnb_properties = await search_airbnb_apify(city, departure, return_date, persons)
            print(f"✅ Found {len(airbnb_properties)} Airbnb properties")
        except Exception as e:
            print(f"❌ Failed to fetch Airbnb properties: {e}")
            # Don't fail the entire search if Airbnb fails - just continue without it
            airbnb_properties = []
            print(f"⚠️ Continuing without Airbnb results")
        
        # Check if we have any results to show
        if not outbound_flights and not return_flights:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"No flights found for {origin_city} ↔ {dest_city} on the selected dates. Please try different dates or destinations."
            })
        
        if not hotels and not airbnb_properties:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"No accommodations found in {city} for the selected dates. Please try different dates or destinations."
            })
        
        # Step 4: Create combinations
        print("🎯 Creating combinations...")
        combinations = create_combinations(
            outbound_flights, return_flights, hotels, airbnb_properties,
            departure, return_date, budget_int, persons
        )
        print(f"✅ Created {len(combinations)} combinations")
        
        # Calculate nights for hotel pricing
        from datetime import datetime
        checkin_date = datetime.strptime(departure, '%Y-%m-%d')
        checkout_date = datetime.strptime(return_date, '%Y-%m-%d')
        nights = (checkout_date - checkin_date).days

        # Export search results to CSV for backup and analysis
        search_params = {
            'origin': f"{origin_city} ({origin_iata})",
            'destination': f"{dest_city} ({dest_iata})",
            'departure': departure,
            'return_date': return_date,
            'persons': persons,
            'budget': budget_int,
            'nights': nights
        }
        export_search_results_to_csv(outbound_flights, return_flights, hotels, airbnb_properties, search_params)

        # Step 5: Render results
        return templates.TemplateResponse("results.html", {
            "request": request,
            "combinations": combinations,
            "outbound_flights": outbound_flights,
            "return_flights": return_flights,
            "hotels": hotels,
            "airbnb_properties": airbnb_properties,
            "origin": f"{origin_city} ({origin_iata})",
            "destination": f"{dest_city} ({dest_iata})",
            "origin_iata": origin_iata,
            "dest_iata": dest_iata,
            "departure": departure,
            "return_date": return_date,
            "checkin": departure,
            "checkout": return_date,
            "nights": nights,
            "budget": budget_int,
            "persons": persons
        })
        
    except Exception as e:
        print(f"❌ Smart search error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/results/{search_id}", response_class=HTMLResponse)
async def show_search_results(request: Request, search_id: str):
    """Show search results from progress search"""
    if search_id not in search_results:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Search results not found or expired."
        })
    
    result_data = search_results[search_id]
    
    return templates.TemplateResponse("results.html", {
        "request": request,
        "combinations": result_data['combinations'],
        "outbound_flights": result_data['outbound_flights'],
        "return_flights": result_data['return_flights'],
        "hotels": result_data['hotels'],
        "airbnb_properties": result_data['airbnb_properties'],
        "origin": result_data['origin'],
        "destination": result_data['destination'],
        "origin_iata": result_data['origin_iata'],
        "dest_iata": result_data['dest_iata'],
        "departure": result_data['departure'],
        "return_date": result_data['return_date'],
        "checkin": result_data['checkin'],
        "checkout": result_data['checkout'],
        "nights": result_data['nights'],
        "budget": result_data['budget'],
        "persons": result_data['persons']
    })

def create_combinations(outbound_flights, return_flights, hotels, airbnb_properties, departure, return_date, budget, persons):
    """Create flight + accommodation combinations (hotels + Airbnb)"""
    print(f"🎯 Creating combinations: {len(outbound_flights)} out + {len(return_flights)} return flights, {len(hotels)} hotels, {len(airbnb_properties)} airbnb")
    combinations = []
    
    # Calculate nights
    from datetime import datetime
    checkin = datetime.strptime(departure, '%Y-%m-%d')
    checkout = datetime.strptime(return_date, '%Y-%m-%d')
    nights = (checkout - checkin).days
    
    print(f"📊 Calculating for {nights} nights, {persons} persons")
    
    # Combine hotels and Airbnb properties for accommodation options
    all_accommodations = []
    
    # Add hotels with type marking
    for hotel in hotels[:3]:
        hotel_copy = hotel.copy()
        hotel_copy['accommodation_type'] = 'hotel'
        all_accommodations.append(hotel_copy)
    
    # Add Airbnb properties with type marking
    for airbnb in airbnb_properties[:3]:
        airbnb_copy = airbnb.copy()
        airbnb_copy['accommodation_type'] = 'airbnb'
        all_accommodations.append(airbnb_copy)
    
    print(f"📊 Total accommodations: {len(hotels)} hotels + {len(airbnb_properties)} Airbnb = {len(all_accommodations)} options")
    
    # Create combinations - check if we have required data first
    if not outbound_flights or not return_flights:
        print("❌ No flights available for combinations")
        return []
    
    if not all_accommodations:
        print("❌ No accommodations available for combinations")
        return []
    
    # Limit to top options for performance
    for out_flight in outbound_flights[:3]:
        for ret_flight in return_flights[:3]:
            for accommodation in all_accommodations:
                
                # Calculate costs
                flight_cost = (out_flight['price'] + ret_flight['price']) * persons
                
                # Handle different accommodation pricing
                if accommodation['accommodation_type'] == 'hotel':
                    accommodation_cost = accommodation['price'] * nights
                    accommodation_label = 'hotel'
                else:  # airbnb
                    # Airbnb price might be per night or total - use per night pricing
                    accommodation_cost = accommodation['price'] * nights
                    accommodation_label = 'airbnb'
                
                total_cost = flight_cost + accommodation_cost
                
                # Budget filter - make it more lenient for testing
                if budget and total_cost > budget * 1.2:  # Allow 20% over budget
                    print(f"  ❌ Combination too expensive: {total_cost}€ > {budget}€ budget")
                    continue
                
                combination = {
                    'outbound_flight': out_flight,
                    'return_flight': ret_flight,
                    'accommodation': accommodation,
                    'accommodation_type': accommodation['accommodation_type'],
                    'flight_cost': flight_cost,
                    'accommodation_cost': accommodation_cost,
                    'total_cost': total_cost,
                    'nights': nights,
                    'persons': persons,
                    'score': calculate_score(total_cost, accommodation['rating'], budget)
                }
                
                combinations.append(combination)
                print(f"  ✅ Combination: {total_cost}€ total ({flight_cost}€ flights + {accommodation_cost}€ {accommodation_label})")
    
    # Sort by score
    combinations.sort(key=lambda x: x['score'], reverse=True)
    print(f"✅ Created {len(combinations)} total combinations, returning top 5")
    return combinations[:5]  # Top 5

def calculate_score(total_cost, accommodation_rating, budget):
    """Simple scoring algorithm for hotels and Airbnb"""
    score = 0
    
    # Accommodation rating (0-50 points)
    score += accommodation_rating * 10
    
    # Budget score (0-50 points)
    if budget:
        if total_cost <= budget * 0.8:  # Under 80% of budget
            score += 50
        elif total_cost <= budget:  # Within budget
            score += 30
        else:  # Over budget (shouldn't happen due to filter)
            score += 0
    else:
        # No budget - prefer lower prices
        score += max(0, 50 - total_cost / 20)
    
    return round(score, 1)

def export_search_results_to_csv(outbound_flights, return_flights, hotels, airbnb_properties, search_params):
    """Export search results to CSV files for backup and analysis"""
    try:
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = f"{search_params['origin']}_{search_params['destination']}_{timestamp}"
        
        # Export flights
        if outbound_flights or return_flights:
            flights_file = os.path.join(output_dir, f"flights_{search_id}.csv")
            with open(flights_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'search_timestamp', 'search_origin', 'search_destination', 'search_departure', 
                    'search_return', 'search_persons', 'search_budget',
                    'flight_type', 'airline', 'departure_time', 'duration', 'stops', 
                    'price_eur', 'source', 'booking_url', 'date'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write outbound flights
                for flight in outbound_flights:
                    writer.writerow({
                        'search_timestamp': timestamp,
                        'search_origin': search_params['origin'],
                        'search_destination': search_params['destination'],
                        'search_departure': search_params['departure'],
                        'search_return': search_params['return_date'],
                        'search_persons': search_params['persons'],
                        'search_budget': search_params.get('budget', ''),
                        'flight_type': 'outbound',
                        'airline': flight.get('airline', ''),
                        'departure_time': flight.get('time', ''),
                        'duration': flight.get('duration', ''),
                        'stops': flight.get('stops', ''),
                        'price_eur': flight.get('price', ''),
                        'source': flight.get('source', ''),
                        'booking_url': flight.get('url', ''),
                        'date': flight.get('date', '')
                    })
                
                # Write return flights
                for flight in return_flights:
                    writer.writerow({
                        'search_timestamp': timestamp,
                        'search_origin': search_params['origin'],
                        'search_destination': search_params['destination'],
                        'search_departure': search_params['departure'],
                        'search_return': search_params['return_date'],
                        'search_persons': search_params['persons'],
                        'search_budget': search_params.get('budget', ''),
                        'flight_type': 'return',
                        'airline': flight.get('airline', ''),
                        'departure_time': flight.get('time', ''),
                        'duration': flight.get('duration', ''),
                        'stops': flight.get('stops', ''),
                        'price_eur': flight.get('price', ''),
                        'source': flight.get('source', ''),
                        'booking_url': flight.get('url', ''),
                        'date': flight.get('date', '')
                    })
            
            print(f"✅ Exported {len(outbound_flights + return_flights)} flights to {flights_file}")
        
        # Export hotels
        if hotels:
            hotels_file = os.path.join(output_dir, f"hotels_{search_id}.csv")
            with open(hotels_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'search_timestamp', 'search_origin', 'search_destination', 'search_departure',
                    'search_return', 'search_persons', 'search_budget', 'nights',
                    'hotel_name', 'rating', 'location', 'type', 'price_total_eur', 
                    'price_per_night_eur', 'source', 'booking_url', 'checkin', 'checkout'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                nights = search_params.get('nights', 1)
                for hotel in hotels:
                    writer.writerow({
                        'search_timestamp': timestamp,
                        'search_origin': search_params['origin'],
                        'search_destination': search_params['destination'],
                        'search_departure': search_params['departure'],
                        'search_return': search_params['return_date'],
                        'search_persons': search_params['persons'],
                        'search_budget': search_params.get('budget', ''),
                        'nights': nights,
                        'hotel_name': hotel.get('name', ''),
                        'rating': hotel.get('rating', ''),
                        'location': hotel.get('location', ''),
                        'type': hotel.get('type', ''),
                        'price_total_eur': hotel.get('price', ''),
                        'price_per_night_eur': round(hotel.get('price', 0) / max(nights, 1), 2),
                        'source': hotel.get('source', ''),
                        'booking_url': hotel.get('url', ''),
                        'checkin': hotel.get('checkin', ''),
                        'checkout': hotel.get('checkout', '')
                    })
            
            print(f"✅ Exported {len(hotels)} hotels to {hotels_file}")
        
        # Export Airbnb properties
        if airbnb_properties:
            airbnb_file = os.path.join(output_dir, f"airbnb_{search_id}.csv")
            with open(airbnb_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'search_timestamp', 'search_origin', 'search_destination', 'search_departure',
                    'search_return', 'search_persons', 'search_budget', 'nights',
                    'property_name', 'rating', 'review_count', 'property_type', 'bedrooms', 'bathrooms',
                    'location', 'host_name', 'is_superhost', 'price_total_eur', 'price_per_night_eur',
                    'amenities', 'source', 'booking_url', 'checkin', 'checkout'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                nights = search_params.get('nights', 1)
                for property in airbnb_properties:
                    # Handle amenities list
                    amenities_str = ', '.join(property.get('amenities', [])[:5])  # First 5 amenities
                    
                    writer.writerow({
                        'search_timestamp': timestamp,
                        'search_origin': search_params['origin'],
                        'search_destination': search_params['destination'],
                        'search_departure': search_params['departure'],
                        'search_return': search_params['return_date'],
                        'search_persons': search_params['persons'],
                        'search_budget': search_params.get('budget', ''),
                        'nights': nights,
                        'property_name': property.get('name', ''),
                        'rating': property.get('rating', ''),
                        'review_count': property.get('review_count', ''),
                        'property_type': property.get('property_type', ''),
                        'bedrooms': property.get('bedrooms', ''),
                        'bathrooms': property.get('bathrooms', ''),
                        'location': property.get('location', ''),
                        'host_name': property.get('host_name', ''),
                        'is_superhost': property.get('is_superhost', ''),
                        'price_total_eur': property.get('total_price', '') or property.get('price', 0) * nights,
                        'price_per_night_eur': property.get('price', ''),
                        'amenities': amenities_str,
                        'source': property.get('source', ''),
                        'booking_url': property.get('url', ''),
                        'checkin': search_params['departure'],
                        'checkout': search_params['return_date']
                    })
            
            print(f"✅ Exported {len(airbnb_properties)} Airbnb properties to {airbnb_file}")
            
        print(f"📁 Search results exported with ID: {search_id}")
        
    except Exception as e:
        print(f"❌ Error exporting search results: {e}")

def get_city_name(iata_code):
    """Convert IATA to city name"""
    cities = {
        'BCN': 'Barcelona',
        'FCO': 'Rome',
        'CDG': 'Paris', 
        'LHR': 'London',
        'AMS': 'Amsterdam',
        'MUC': 'Munich',
        'VIE': 'Vienna',
        'ZUR': 'Zurich'
    }
    return cities.get(iata_code, iata_code)

# Simple endpoints for testing
@app.post("/flights-only")
async def flights_only(origin: str = Form(...), destination: str = Form(...), date: str = Form(...)):
    """Simple flight search"""
    flights = await search_flights_apify(origin, destination, date)
    return {"flights": flights}

@app.post("/hotels-only") 
async def hotels_only(city: str = Form(...), checkin: str = Form(...), checkout: str = Form(...)):
    """Simple hotel search"""
    hotels = await search_hotels_apify(city, checkin, checkout)
    return {"hotels": hotels}

if __name__ == "__main__":
    import uvicorn
    
    # Check if templates directory exists
    if not os.path.exists("templates"):
        print("❌ Error: 'templates' directory not found!")
        print("💡 Please create templates/ directory with HTML files")
        exit(1)
    
    print("🚀 Starting Travel Platform...")
    print("🌐 Open: http://localhost:8000")
    print("🔧 Health: http://localhost:8000/health")
    print("🧪 Test: http://localhost:8000/test-flights")
    
    # Fix: Remove reload for direct run
    uvicorn.run(app, host="0.0.0.0", port=8000)