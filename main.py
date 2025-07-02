# main.py - Clean FastAPI Travel App
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import os
from datetime import datetime, timedelta

# Import deine bestehende API
from travel_api import search_flights_apify, search_hotels_apify

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
    budget: int = Form(None),
    persons: int = Form(2)
):
    """Smart travel search with combinations"""
    try:
        print(f"🧠 Smart Search: {origin}→{destination}, {persons} persons, budget: {budget}")
        
        # Step 1: Search flights
        print("📡 Searching outbound flights...")
        outbound_flights = await search_flights_apify(origin, destination, departure)
        print(f"✅ Found {len(outbound_flights)} outbound flights")
        
        print("📡 Searching return flights...")
        return_flights = await search_flights_apify(destination, origin, return_date)
        print(f"✅ Found {len(return_flights)} return flights")
        
        # Step 2: Search hotels
        city = get_city_name(destination)
        print(f"📡 Searching hotels in {city}...")
        hotels = await search_hotels_apify(city, departure, return_date)
        print(f"✅ Found {len(hotels)} hotels")
        
        # Step 3: Create combinations
        print("🎯 Creating combinations...")
        combinations = create_combinations(
            outbound_flights, return_flights, hotels, 
            departure, return_date, budget, persons
        )
        print(f"✅ Created {len(combinations)} combinations")
        
        # Step 4: Render results
        return templates.TemplateResponse("results.html", {
            "request": request,  # ← Fix: Pass the actual request object
            "combinations": combinations,
            "origin": origin,
            "destination": destination,
            "budget": budget,
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