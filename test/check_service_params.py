# check_service_params.py
"""
Prüfe die exakten Parameter deiner Services
"""

import inspect
import os
from dotenv import load_dotenv
load_dotenv()

def check_all_service_params():
    """Zeige alle Service-Parameter"""
    
    try:
        from utils.api_client import ApifyClient
        from services.city_resolver import CityResolverService
        from services.flight_service import FlightService
        from services.hotel_service import AccommodationService
        
        api_client = ApifyClient(os.getenv("APIFY_TOKEN", "demo"))
        
        print("🔍 Service Parameter Analyse:")
        
        # CityResolver
        city_resolver = CityResolverService()
        print("\n✅ CityResolverService.resolve_to_iata():")
        sig = inspect.signature(city_resolver.resolve_to_iata)
        print(f"   Signature: {sig}")
        
        # FlightService
        flight_service = FlightService(api_client)
        print("\n✅ FlightService.search_round_trip():")
        sig = inspect.signature(flight_service.search_round_trip)
        print(f"   Signature: {sig}")
        
        # AccommodationService
        hotel_service = AccommodationService(api_client)
        print("\n✅ AccommodationService Methoden:")
        methods = [method for method in dir(hotel_service) if not method.startswith('_') and callable(getattr(hotel_service, method))]
        for method in methods:
            if 'search' in method:
                print(f"   • {method}")
                try:
                    sig = inspect.signature(getattr(hotel_service, method))
                    print(f"     Signature: {sig}")
                except:
                    print(f"     Signature: nicht verfügbar")
        
        # Test CityResolver Output
        print("\n🧪 Teste CityResolver Output:")
        result = city_resolver.resolve_to_iata("Italien")
        print(f"   Italien → {result}")
        print(f"   Type: {type(result)}")
        
        if isinstance(result, tuple) and len(result) >= 1:
            print(f"   IATA Code: {result[0]}")
        elif isinstance(result, list) and len(result) >= 1:
            print(f"   IATA Code: {result[0]}")
        elif isinstance(result, str):
            print(f"   IATA Code: {result}")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_all_service_params()