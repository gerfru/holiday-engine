# main.py - Clean FastAPI Travel App
from fastapi import FastAPI, Request, Form
from typing import Optional
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
import csv
from datetime import datetime, timedelta

# Import deine bestehende API
from travel_api import search_flights_apify, search_hotels_apify
from smart_city_lookup import hybrid_city_to_iata

# FastAPI Setup
app = FastAPI(title="Travel Comparison Platform")

# Templates setup
templates = Jinja2Templates(directory="templates")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "travel-platform"}

# Main page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Hauptseite - lädt HTML Template"""
    return templates.TemplateResponse("index.html", {"request": request})

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
        
        # Step 0: Resolve city names to IATA codes
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
        
        # Check if we have any results to show
        if not outbound_flights and not return_flights:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"No flights found for {origin_city} ↔ {dest_city} on the selected dates. Please try different dates or destinations."
            })
        
        if not hotels:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": f"No hotels found in {city} for the selected dates. Please try different dates or destinations."
            })
        
        # Step 3: Create combinations
        print("🎯 Creating combinations...")
        combinations = create_combinations(
            outbound_flights, return_flights, hotels, 
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
        export_search_results_to_csv(outbound_flights, return_flights, hotels, search_params)

        # Step 4: Render results
        return templates.TemplateResponse("results.html", {
            "request": request,
            "combinations": combinations,
            "outbound_flights": outbound_flights,
            "return_flights": return_flights,
            "hotels": hotels,
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
            "request": request,  # ← Fix: Pass the actual request object
            "error": str(e)
        })

def create_combinations(outbound_flights, return_flights, hotels, departure, return_date, budget, persons):
    """Create flight + hotel combinations"""
    combinations = []
    
    # Calculate nights
    from datetime import datetime
    checkin = datetime.strptime(departure, '%Y-%m-%d')
    checkout = datetime.strptime(return_date, '%Y-%m-%d')
    nights = (checkout - checkin).days
    
    print(f"📊 Calculating for {nights} nights, {persons} persons")
    
    # Limit to top options for performance
    for out_flight in outbound_flights[:3]:
        for ret_flight in return_flights[:3]:
            for hotel in hotels[:3]:
                
                # Calculate costs
                flight_cost = (out_flight['price'] + ret_flight['price']) * persons
                hotel_cost = hotel['price'] * nights
                total_cost = flight_cost + hotel_cost
                
                # Budget filter - make it more lenient for testing
                if budget and total_cost > budget * 1.2:  # Allow 20% over budget
                    print(f"  ❌ Combination too expensive: {total_cost}€ > {budget}€ budget")
                    continue
                
                combination = {
                    'outbound_flight': out_flight,
                    'return_flight': ret_flight,
                    'hotel': hotel,
                    'flight_cost': flight_cost,
                    'hotel_cost': hotel_cost,
                    'total_cost': total_cost,
                    'nights': nights,
                    'persons': persons,
                    'score': calculate_score(total_cost, hotel['rating'], budget)
                }
                
                combinations.append(combination)
                print(f"  ✅ Combination: {total_cost}€ total ({flight_cost}€ flights + {hotel_cost}€ hotel)")
            
        print(f"🔍 Generated {len(combinations)} combinations from this flight combo")
    
    # Sort by score
    combinations.sort(key=lambda x: x['score'], reverse=True)
    return combinations[:5]  # Top 5

def calculate_score(total_cost, hotel_rating, budget):
    """Simple scoring algorithm"""
    score = 0
    
    # Hotel rating (0-50 points)
    score += hotel_rating * 10
    
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

def export_search_results_to_csv(outbound_flights, return_flights, hotels, search_params):
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