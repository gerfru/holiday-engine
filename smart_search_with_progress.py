# smart_search_with_progress.py - Smart search with real-time progress
import asyncio
import uuid
from datetime import datetime
from fastapi import Request, Form
from fastapi.responses import RedirectResponse
from travel_api import search_flights_apify, search_hotels_apify, search_airbnb_apify
from smart_city_lookup_simple import hybrid_city_to_iata

async def smart_search_with_progress(
    origin: str,
    destination: str, 
    departure: str,
    return_date: str,
    budget: str = None,
    persons: int = 2,
    progress_callback = None
):
    """
    Smart travel search with progress tracking
    
    Args:
        progress_callback: Function to call with progress updates
                          progress_callback(step, message, progress, results)
    """
    
    # Generate search ID
    search_id = str(uuid.uuid4())[:8]
    
    try:
        # Convert budget to integer if provided
        budget_int = None
        if budget and budget.strip():
            try:
                budget_int = int(budget)
            except ValueError:
                budget_int = None
        
        print(f"🧠 Smart Search with Progress: {origin}→{destination}, {persons} persons, budget: {budget_int}")
        
        # Step 1: City Resolution (20% progress)
        if progress_callback:
            progress_callback("city_resolution", "Städte werden aufgelöst...", 10)
        
        print(f"🔍 Resolving origin city: {origin}")
        origin_iata, origin_city, origin_suggestions = await hybrid_city_to_iata(origin)
        if not origin_iata:
            if progress_callback:
                progress_callback("error", f"Startstadt '{origin}' nicht gefunden", 0)
            return {"error": f"Origin city '{origin}' not found. Suggestions: {', '.join(origin_suggestions[:3]) if origin_suggestions else 'None'}"}
        
        print(f"🔍 Resolving destination city: {destination}")
        dest_iata, dest_city, dest_suggestions = await hybrid_city_to_iata(destination)
        if not dest_iata:
            if progress_callback:
                progress_callback("error", f"Zielstadt '{destination}' nicht gefunden", 0)
            return {"error": f"Destination city '{destination}' not found. Suggestions: {', '.join(dest_suggestions[:3]) if dest_suggestions else 'None'}"}
        
        print(f"✅ Resolved: {origin} → {origin_iata}, {destination} → {dest_iata}")
        if progress_callback:
            progress_callback("city_resolution", f"Städte aufgelöst: {origin_city} → {dest_city}", 20)
        
        # Step 2: Flight Search (40% progress)
        if progress_callback:
            progress_callback("flight_search_outbound", "Hinflüge werden gesucht...", 25)
        
        print("📡 Searching outbound flights...")
        outbound_flights = await search_flights_apify(origin_iata, dest_iata, departure)
        print(f"✅ Found {len(outbound_flights)} outbound flights")
        
        if progress_callback:
            progress_callback("flight_search_return", "Rückflüge werden gesucht...", 35)
        
        print("📡 Searching return flights...")
        return_flights = await search_flights_apify(dest_iata, origin_iata, return_date)
        print(f"✅ Found {len(return_flights)} return flights")
        
        if progress_callback:
            progress_callback("flight_search_return", f"{len(outbound_flights + return_flights)} Flüge gefunden", 40)
        
        # Step 3: Hotel Search (60% progress)
        if progress_callback:
            progress_callback("hotel_search", "Hotels werden gesucht...", 45)
        
        city = dest_city
        print(f"📡 Searching hotels in {city}...")
        hotels = await search_hotels_apify(city, departure, return_date)
        print(f"✅ Found {len(hotels)} hotels")
        
        if progress_callback:
            progress_callback("hotel_search", f"{len(hotels)} Hotels gefunden", 60)
        
        # Step 4: Airbnb Search (80% progress)
        if progress_callback:
            progress_callback("airbnb_search", "Airbnb-Unterkünfte werden gesucht...", 65)
        
        print(f"📡 Searching Airbnb properties in {city}...")
        airbnb_properties = await search_airbnb_apify(city, departure, return_date, persons)
        print(f"✅ Found {len(airbnb_properties)} Airbnb properties")
        
        if progress_callback:
            progress_callback("airbnb_search", f"{len(airbnb_properties)} Airbnb-Unterkünfte gefunden", 80)
        
        # Check if we have results
        if not outbound_flights and not return_flights:
            if progress_callback:
                progress_callback("error", "Keine Flüge gefunden", 80)
            return {"error": f"No flights found for {origin_city} ↔ {dest_city} on the selected dates."}
        
        if not hotels and not airbnb_properties:
            if progress_callback:
                progress_callback("error", "Keine Unterkünfte gefunden", 80)
            return {"error": f"No accommodations found in {city} for the selected dates."}
        
        # Step 5: Create Combinations (100% progress)
        if progress_callback:
            progress_callback("combination_creation", "Beste Kombinationen werden erstellt...", 85)
        
        print("🎯 Creating combinations...")
        from main import create_combinations  # Import here to avoid circular imports
        combinations = create_combinations(
            outbound_flights, return_flights, hotels, airbnb_properties,
            departure, return_date, budget_int, persons
        )
        print(f"✅ Created {len(combinations)} combinations")
        
        # Calculate nights for hotel pricing
        checkin_date = datetime.strptime(departure, '%Y-%m-%d')
        checkout_date = datetime.strptime(return_date, '%Y-%m-%d')
        nights = (checkout_date - checkin_date).days
        
        # Final results
        results_summary = {
            "flights": len(outbound_flights + return_flights),
            "hotels": len(hotels),
            "airbnb": len(airbnb_properties),
            "combinations": len(combinations)
        }
        
        if progress_callback:
            progress_callback("completed", "Suche abgeschlossen!", 100, results_summary)
        
        # Store results for the results page (you might want to use a proper cache like Redis)
        result_data = {
            "combinations": combinations,
            "origin_city": origin_city,
            "dest_city": dest_city,
            "departure": departure,
            "return_date": return_date,
            "nights": nights,
            "persons": persons,
            "budget": budget_int,
            "search_params": {
                'origin': f"{origin_city} ({origin_iata})",
                'destination': f"{dest_city} ({dest_iata})",
                'departure': departure,
                'return_date': return_date,
                'persons': persons,
                'budget': budget_int
            }
        }
        
        return {
            "success": True,
            "search_id": search_id,
            "results": result_data,
            "summary": results_summary
        }
        
    except Exception as e:
        print(f"❌ Search Error: {e}")
        if progress_callback:
            progress_callback("error", f"Fehler: {str(e)[:50]}...", 0)
        return {"error": str(e)}