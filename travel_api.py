# travel_api.py - Geteilte API Funktionen für MCP Server und Web App
import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

async def search_flights_apify(origin: str, destination: str, date: str):
    """Echte Flugsuche über Apify Skyscanner"""
    print(f"🔍 APIFY: Suche Flüge {origin} → {destination} am {date}")
    
    if not APIFY_TOKEN:
        print("❌ Kein Apify Token, verwende Mock")
        return await mock_flight_search(origin, destination, date)
    
    # Skyscanner Actor Input Format
    actor_input = {
        "origin.0": origin.upper(),
        "target.0": destination.upper(),
        "depart.0": date  # YYYY-MM-DD Format ist ok
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("📡 Starte Skyscanner Actor...")
            print(f"📋 Input: {actor_input}")
            response = await client.post(
                "https://api.apify.com/v2/acts/jupri~skyscanner-flight/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {APIFY_TOKEN}"},
                json=actor_input
            )
            
            # Akzeptiere sowohl 200 als auch 201 als Erfolg
            if response.status_code not in [200, 201]:
                print(f"❌ Skyscanner Fehler: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return await mock_flight_search(origin, destination, date)
            
            data = response.json()
            print(f"✅ Skyscanner Response: {len(data)} Ergebnisse")
            
            # Debug: Zeige ersten Eintrag (gekürzt)
            if data:
                first_item = data[0]
                print(f"🔍 Response Struktur erkannt:")
                print(f"   - Keys: {list(first_item.keys())[:5]}...")  # Erste 5 Keys
                if '_agents' in first_item:
                    print(f"   - Agents gefunden: {len(first_item['_agents'])}")
                
                # Suche nach Flugdaten in der Response
                if 'itineraries' in first_item:
                    print(f"   - Itineraries gefunden: {len(first_item.get('itineraries', []))}")
                elif 'legs' in first_item:
                    print(f"   - Legs gefunden: {len(first_item.get('legs', []))}")
                elif 'segments' in first_item:
                    print(f"   - Segments gefunden: {len(first_item.get('segments', []))}")
            
            # Parse Skyscanner Response
            flights = parse_skyscanner_response(data)
            
            if not flights:
                print("⚠️  Keine verwertbaren Flüge gefunden, verwende Mock")
                return await mock_flight_search(origin, destination, date)
            
            print(f"✅ {len(flights)} Flüge erfolgreich konvertiert")
            return flights
            
    except Exception as e:
        print(f"❌ Skyscanner API Fehler: {e}")
        print("🔄 Fallback zu Mock")
        return await mock_flight_search(origin, destination, date)

def parse_skyscanner_response(data):
    """Parst die echte Skyscanner Response Struktur"""
    flights = []
    
    try:
        if not data or not isinstance(data, list):
            print("⚠️  Unerwartete Response Struktur")
            return flights
        
        # Verarbeite jedes Skyscanner Result Item
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Extrahiere Lookup-Tabellen
            carriers = item.get('_carriers', {})
            places = item.get('_places', {})
            segments = item.get('_segments', {})
            
            # Extrahiere Flugdaten
            legs = item.get('legs', [])
            pricing_options = item.get('pricing_options', [])
            
            if not legs or not pricing_options:
                print(f"⚠️  Item ohne legs oder pricing_options übersprungen")
                continue
            
            # Verarbeite jede Pricing Option (= ein buchbarer Flug)
            for pricing_option in pricing_options[:5]:  # Max 5 pro Item
                try:
                    flight = parse_single_skyscanner_flight(
                        pricing_option, legs, carriers, places, segments
                    )
                    if flight:
                        flights.append(flight)
                except Exception as e:
                    print(f"⚠️  Fehler beim Parsen einer Pricing Option: {e}")
                    continue
            
            # Maximal 10 Flüge total
            if len(flights) >= 10:
                break
        
        # Sortiere nach Preis (günstigste zuerst)
        flights.sort(key=lambda x: x.get('price', 999999))
        print(f"✅ {len(flights)} Flüge erfolgreich geparst")
        return flights[:5]  # Top 5
        
    except Exception as e:
        print(f"❌ Parser Fehler: {e}")
        return flights

def parse_single_skyscanner_flight(pricing_option, legs, carriers, places, segments):
    """Parst einen einzelnen Skyscanner Flug"""
    try:
        # Preis aus pricing_option
        price_info = pricing_option.get('price', {})
        price = price_info.get('amount', 0)
        
        # Ersten Leg nehmen (Outbound)
        if not legs:
            return None
        
        main_leg = legs[0]
        
        # Carrier Information
        marketing_carrier_ids = main_leg.get('marketing_carrier_ids', [])
        airline = "Unknown"
        if marketing_carrier_ids and carriers:
            carrier_id = str(marketing_carrier_ids[0])
            if carrier_id in carriers:
                airline = carriers[carrier_id].get('name', 'Unknown')
        
        # Zeiten
        departure_time = main_leg.get('departure', 'Unknown')
        arrival_time = main_leg.get('arrival', 'Unknown')
        
        # Formatiere Zeit (von ISO zu HH:MM)
        formatted_departure = format_time(departure_time)
        
        # Dauer (in Minuten -> h:mm Format)
        duration_minutes = main_leg.get('duration', 0)
        formatted_duration = format_duration(duration_minutes)
        
        # Zusätzliche Infos
        stop_count = main_leg.get('stop_count', 0)
        stops_text = f" ({stop_count} Stops)" if stop_count > 0 else " (Nonstop)"
        
        flight = {
            'airline': airline,
            'price': int(price) if price else 0,
            'time': formatted_departure,
            'duration': formatted_duration + stops_text
        }
        
        print(f"  ✈️  {airline}: {price}€ um {formatted_departure} ({formatted_duration})")
        return flight
        
    except Exception as e:
        print(f"❌ Fehler beim Parsen eines Flugs: {e}")
        return None

def format_time(iso_time_str):
    """Konvertiert ISO Zeitstempel zu HH:MM Format"""
    try:
        if iso_time_str == 'Unknown' or not iso_time_str:
            return 'Unknown'
        
        # ISO Format: 2025-08-15T08:30:00
        from datetime import datetime
        dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        return dt.strftime('%H:%M')
    except:
        return str(iso_time_str)[:5] if iso_time_str else 'Unknown'

def format_duration(minutes):
    """Konvertiert Minuten zu h:mm Format"""
    try:
        if not minutes or minutes == 0:
            return 'Unknown'
        
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins:02d}m"
    except:
        return 'Unknown'

# Die alten extract_* Funktionen werden nicht mehr benötigt

async def search_hotels_apify(city: str, checkin: str, checkout: str):
    """Hotelsuche über Apify (später implementieren)"""
    print(f"🏨 TODO: Echte Hotelsuche für {city}")
    return await mock_hotel_search(city, checkin, checkout)

# Mock Backup Funktionen
async def mock_flight_search(origin: str, destination: str, date: str):
    """Mock Backup"""
    print(f"🔄 MOCK: Flüge {origin} → {destination}")
    await asyncio.sleep(0.5)
    return [
        {"airline": "Lufthansa", "price": 299, "time": "08:30", "duration": "3h 15m"},
        {"airline": "Austrian Airlines", "price": 259, "time": "14:20", "duration": "3h 30m"},
        {"airline": "Eurowings", "price": 199, "time": "06:45", "duration": "3h 20m"}
    ]

async def mock_hotel_search(city: str, checkin: str, checkout: str):
    """Mock Hotels"""
    print(f"🔄 MOCK: Hotels in {city}")
    await asyncio.sleep(0.3)
    hotels = [
        {"name": "Hotel Sacher", "price": 280, "rating": 4.8, "location": "Zentrum"},
        {"name": "Austria Trend Hotel", "price": 150, "rating": 4.2, "location": "Innenstadt"},
        {"name": "Budget Inn", "price": 89, "rating": 3.8, "location": "Außenbezirk"}
    ]
    
    # Füge Sterne für Web GUI hinzu
    for hotel in hotels:
        hotel["stars"] = "⭐" * int(hotel["rating"])
    
    return hotels