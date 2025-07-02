# test_scrapers.py - Test and Debug Travel API Scrapers
import asyncio
import time
from travel_api import search_flights_apify, search_hotels_apify, search_airbnb_apify

async def test_scrapers():
    """Test all scrapers with debugging information"""
    
    print("🧪 Travel API Scraper Test & Debug")
    print("=" * 50)
    
    # Test parameters
    test_cases = [
        {
            "origin": "VIE",
            "destination": "BCN", 
            "city": "Barcelona",
            "checkin": "2025-08-15",
            "checkout": "2025-08-17",
            "departure": "2025-08-15",
            "return_date": "2025-08-17",
            "guests": 2
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}: {test_case['origin']} → {test_case['destination']}")
        print(f"   City: {test_case['city']}")
        print(f"   Dates: {test_case['checkin']} to {test_case['checkout']}")
        print(f"   Guests: {test_case['guests']}")
        print("-" * 50)
        
        # Test 1: Flight Search
        print("\n✈️ Testing Flight Search (Skyscanner)...")
        flight_start = time.time()
        try:
            flights = await search_flights_apify(
                test_case['origin'], 
                test_case['destination'], 
                test_case['departure']
            )
            flight_duration = time.time() - flight_start
            
            print(f"✅ Flight Search Results:")
            print(f"   • Duration: {flight_duration:.1f} seconds")
            print(f"   • Results: {len(flights)} flights found")
            
            if flights:
                print(f"   • Sample flight: {flights[0]['airline']} - €{flights[0]['price']} at {flights[0]['time']}")
                print(f"   • Price range: €{min(f['price'] for f in flights)} - €{max(f['price'] for f in flights)}")
            else:
                print("   ⚠️ No flights found")
                
        except Exception as e:
            flight_duration = time.time() - flight_start
            print(f"❌ Flight Search Failed:")
            print(f"   • Duration: {flight_duration:.1f} seconds")
            print(f"   • Error: {str(e)[:100]}")
        
        # Test 2: Hotel Search (Booking.com)
        print("\n🏨 Testing Hotel Search (Booking.com - NEW: 200 limit)...")
        hotel_start = time.time()
        hotels = []  # Initialize variable
        try:
            hotels = await search_hotels_apify(
                test_case['city'],
                test_case['checkin'],
                test_case['checkout']
            )
            hotel_duration = time.time() - hotel_start
            
            print(f"✅ Hotel Search Results:")
            print(f"   • Duration: {hotel_duration:.1f} seconds")
            print(f"   • Results: {len(hotels)} hotels found")
            print(f"   • Expected: ~50 hotels (from 200 scraped)")
            
            if hotels:
                print(f"   • Sample hotel: {hotels[0]['name']} - €{hotels[0]['price']} ⭐{hotels[0]['rating']}")
                print(f"   • Price range: €{min(h['price'] for h in hotels)} - €{max(h['price'] for h in hotels)}")
                print(f"   • Rating range: {min(h['rating'] for h in hotels):.1f} - {max(h['rating'] for h in hotels):.1f}")
            else:
                print("   ⚠️ No hotels found")
                
        except Exception as e:
            hotel_duration = time.time() - hotel_start
            print(f"❌ Hotel Search Failed:")
            print(f"   • Duration: {hotel_duration:.1f} seconds")
            print(f"   • Error: {str(e)[:100]}")
        
        # Test 3: Airbnb Search (NEW: Limited to 100)
        print("\n🏠 Testing Airbnb Search (NEW: Limited to 100 results)...")
        airbnb_start = time.time()
        airbnb_properties = []  # Initialize variable
        try:
            airbnb_properties = await search_airbnb_apify(
                test_case['city'],
                test_case['checkin'],
                test_case['checkout'],
                test_case['guests']
            )
            airbnb_duration = time.time() - airbnb_start
            
            print(f"✅ Airbnb Search Results:")
            print(f"   • Duration: {airbnb_duration:.1f} seconds")
            print(f"   • Results: {len(airbnb_properties)} properties found")
            print(f"   • Expected: ≤100 properties (HARD LIMIT)")
            print(f"   • Performance: Should be much faster than before!")
            
            if airbnb_properties:
                print(f"   • Sample property: {airbnb_properties[0]['name']} - €{airbnb_properties[0]['price']}/night ⭐{airbnb_properties[0]['rating']}")
                print(f"   • Price range: €{min(a['price'] for a in airbnb_properties)} - €{max(a['price'] for a in airbnb_properties)}/night")
                print(f"   • Property types: {set(a['property_type'] for a in airbnb_properties[:5])}")
            else:
                print("   ⚠️ No Airbnb properties found")
                
        except Exception as e:
            airbnb_duration = time.time() - airbnb_start
            print(f"❌ Airbnb Search Failed:")
            print(f"   • Duration: {airbnb_duration:.1f} seconds")
            print(f"   • Error: {str(e)[:100]}")
        
        # Summary for this test case
        total_time = (time.time() - flight_start)
        print(f"\n📊 Test Case {i} Summary:")
        print(f"   • Total Duration: {total_time:.1f} seconds")
        print(f"   • Flight Duration: {flight_duration:.1f}s")
        print(f"   • Hotel Duration: {hotel_duration:.1f}s") 
        print(f"   • Airbnb Duration: {airbnb_duration:.1f}s")
        
        # Performance expectations
        print(f"\n🎯 Performance Expectations vs Reality:")
        print(f"   • Flights: Expected ~30s, Got {flight_duration:.1f}s")
        print(f"   • Hotels: Expected ~45s, Got {hotel_duration:.1f}s (NEW: 200 limit)")
        print(f"   • Airbnb: Expected ~30s, Got {airbnb_duration:.1f}s (NEW: 100 limit)")
        
        if airbnb_duration < 45:
            print("   ✅ Airbnb performance improvement SUCCESS!")
        else:
            print("   ⚠️ Airbnb still slow - check configuration")
            
        if len(hotels) > 20:
            print("   ✅ Hotel results improvement SUCCESS!")
        else:
            print("   ⚠️ Hotel results still low - check configuration")


async def debug_airbnb_specifically():
    """Specific debug test for Airbnb scraper"""
    
    print("\n" + "=" * 50)
    print("🔍 AIRBNB SCRAPER DEBUG MODE")
    print("=" * 50)
    
    test_cities = ["Barcelona", "Paris", "Rome"]
    
    for city in test_cities:
        print(f"\n🏠 Testing Airbnb in {city}...")
        start_time = time.time()
        
        try:
            properties = await search_airbnb_apify(city, "2025-08-15", "2025-08-17", 2)
            duration = time.time() - start_time
            
            print(f"✅ {city} Results:")
            print(f"   • Count: {len(properties)} properties")
            print(f"   • Duration: {duration:.1f} seconds")
            print(f"   • Expected: ≤100 properties (due to limit)")
            
            if len(properties) > 100:
                print("   ⚠️ WARNING: More than 100 results returned - limit not working!")
            elif len(properties) > 50:
                print("   ✅ Good result count within limits")
            elif len(properties) > 0:
                print("   ⚠️ Low result count - may need to adjust search parameters")
            else:
                print("   ❌ No results - check search configuration")
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {city} Failed: {str(e)[:100]}")
            print(f"   • Duration: {duration:.1f} seconds")


async def main():
    """Main test runner"""
    print("🚀 Starting Travel API Scraper Tests...")
    
    # Run main tests
    await test_scrapers()
    
    # Run specific Airbnb debug
    await debug_airbnb_specifically()
    
    print(f"\n🎉 Test Complete!")
    print(f"💡 Key Things to Check:")
    print(f"   • Airbnb should be faster (~30-45s) and limited to ≤100 results")
    print(f"   • Hotels should return 20-50 results (from 200 scraped)")
    print(f"   • All scrapers should complete without errors")


if __name__ == "__main__":
    asyncio.run(main())