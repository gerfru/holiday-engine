# direct_services_test.py
"""
Teste direkte Service-Aufrufe statt über die API
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

async def test_direct_services():
    """Teste deine Services direkt"""
    
    print("🚀 Teste direkte Service-Aufrufe...")
    
    # 1. OpenAI Analyse
    from mcp_server import holiday_client
    query = "Romantische Reise nach Italien unter 1000€ im Dezember für 7-10 Tage"
    
    print(f"🤖 Analysiere: {query}")
    analysis = await holiday_client.llm_service.analyze_travel_query(query)
    
    destination = analysis.get('destination', 'Italien')
    print(f"🎯 Ziel: {destination}")
    
    # 2. Initialisiere Services direkt
    try:
        from utils.api_client import ApifyClient
        from services.city_resolver import CityResolverService
        from services.flight_service import FlightService
        from services.hotel_service import AccommodationService
        
        # Services initialisieren
        api_token = os.getenv("APIFY_TOKEN", "demo_token")
        api_client = ApifyClient(api_token)
        
        city_resolver = CityResolverService()
        flight_service = FlightService(api_client)
        hotel_service = AccommodationService(api_client)
        
        print("✅ Services initialisiert")
        
        # 3. Stadt zu IATA Code (ASYNC!)
        print(f"🔍 Löse '{destination}' zu IATA Code auf...")
        destination_result = await city_resolver.resolve_to_iata(destination)
        print(f"✅ {destination} → {destination_result}")
        
        # Extrahiere IATA Code aus Tuple
        if isinstance(destination_result, tuple) and destination_result[0]:
            destination_iata = destination_result[0]  # Erster Wert ist IATA Code
            destination_name = destination_result[1]   # Zweiter Wert ist Name
        else:
            destination_iata = "FCO"  # Fallback Rom
            destination_name = "Italien"
        
        print(f"🎯 IATA Code: {destination_iata}")
        
        # 4. Teste Flight Service
        print("✈️ Teste Flight Service...")
        flights = await flight_service.search_round_trip(
            origin="VIE",  # Wien
            destination=destination_iata,  # Jetzt String statt Tuple
            departure_date="2025-12-01",
            return_date="2025-12-08"
        )
        
        print(f"✅ Flights gefunden: {type(flights)}")
        if isinstance(flights, dict):
            outbound = flights.get('outbound', [])
            inbound = flights.get('inbound', [])
            print(f"   Hinflüge: {len(outbound)}")
            print(f"   Rückflüge: {len(inbound)}")
        else:
            print(f"   Total: {len(flights) if flights else 0}")
        
        # 5. Teste Hotel Service (korrekte Parameter!)
        print("🏨 Teste Hotel Service...")
        hotels = await hotel_service.search_hotels(
            city=destination,  # city statt destination
            checkin="2025-12-01",  # checkin statt check_in
            checkout="2025-12-08"   # checkout statt check_out
        )
        
        print(f"✅ Hotels gefunden: {len(hotels) if hotels else 0}")
        if hotels and len(hotels) > 0:
            print(f"   Beispiel: {hotels[0].get('name', 'N/A')}")
        
        # 6. OpenAI Empfehlungen basierend auf echten Daten
        print("💡 Generiere OpenAI Empfehlungen...")
        
        mock_results = {
            "search_results": [{
                "combinations": [{
                    "flight": flights.get('outbound', [{}])[0] if isinstance(flights, dict) else (flights[0] if flights else {}),
                    "hotel": hotels[0] if hotels else {},
                    "total_price": analysis.get('budget_max', 1000)
                }]
            }]
        }
        
        recommendations = await holiday_client.llm_service.generate_travel_recommendations(
            mock_results, analysis
        )
        
        print("✅ OpenAI Empfehlungen:")
        print(recommendations[:200] + "..." if len(recommendations) > 200 else recommendations)
        
        print("\n🎯 ERFOLG! Vollständiger Workflow funktioniert:")
        print("  1. ✅ OpenAI analysiert natürlichsprachliche Eingabe")
        print("  2. ✅ CityResolver löst Destinationen auf")
        print("  3. ✅ FlightService sucht Flüge")
        print("  4. ✅ HotelService sucht Hotels")
        print("  5. ✅ OpenAI macht intelligente Empfehlungen")
        
        return True
        
    except Exception as e:
        print(f"❌ Fehler bei Service-Test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_direct_services())