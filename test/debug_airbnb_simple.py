# debug_airbnb_simple.py - Simple Airbnb Scraper Debug
import asyncio
import time
from travel_api import search_airbnb_apify

async def debug_airbnb_single_city():
    """Debug Airbnb scraper with one city only"""
    
    print("🔍 AIRBNB SCRAPER DEBUG - Single City Test")
    print("=" * 50)
    
    # Test parameters
    city = "Barcelona"
    checkin = "2025-08-15"
    checkout = "2025-08-17"
    guests = 2
    
    print(f"🏠 Testing Airbnb in: {city}")
    print(f"📅 Dates: {checkin} to {checkout}")
    print(f"👥 Guests: {guests}")
    print(f"🎯 Expected: ≤100 results, ~30-45 seconds")
    print("-" * 50)
    
    # Start timing
    start_time = time.time()
    
    try:
        print("📡 Starting Airbnb search...")
        properties = await search_airbnb_apify(city, checkin, checkout, guests)
        duration = time.time() - start_time
        
        print(f"\n✅ AIRBNB SEARCH COMPLETED")
        print(f"⏱️  Duration: {duration:.1f} seconds")
        print(f"📊 Results: {len(properties)} properties found")
        print(f"🎯 Limit check: {'✅ WORKING' if len(properties) <= 100 else '❌ OVER LIMIT'}")
        print(f"⚡ Speed check: {'✅ FAST' if duration < 60 else '⚠️ SLOW'}")
        
        if properties:
            print(f"\n📋 Sample Results:")
            for i, prop in enumerate(properties[:3], 1):
                print(f"   {i}. {prop['name'][:40]} - €{prop['price']}/night ⭐{prop['rating']}")
            
            print(f"\n📈 Statistics:")
            prices = [p['price'] for p in properties if p['price'] > 0]
            ratings = [p['rating'] for p in properties if p['rating'] > 0]
            
            if prices:
                print(f"   💰 Price range: €{min(prices)} - €{max(prices)}/night")
                print(f"   💰 Average price: €{sum(prices)/len(prices):.0f}/night")
            
            if ratings:
                print(f"   ⭐ Rating range: {min(ratings):.1f} - {max(ratings):.1f}")
                print(f"   ⭐ Average rating: {sum(ratings)/len(ratings):.1f}")
            
            property_types = list(set(p.get('property_type', 'Unknown') for p in properties[:10]))
            print(f"   🏠 Property types: {', '.join(property_types)}")
        
        else:
            print("\n❌ NO RESULTS FOUND")
            print("   Check:")
            print("   • API token is valid")
            print("   • City name is correct")
            print("   • Date format is YYYY-MM-DD")
            print("   • Actor configuration")
        
        # Performance analysis
        print(f"\n🧪 DEBUG ANALYSIS:")
        print(f"   • Expected duration: 30-45 seconds")
        print(f"   • Actual duration: {duration:.1f} seconds")
        print(f"   • Expected results: ≤100")
        print(f"   • Actual results: {len(properties)}")
        
        if duration > 60:
            print(f"   ⚠️  SLOW: Possible issues:")
            print(f"      - maxItems limit not working")
            print(f"      - Actor still scraping all results")
            print(f"      - Network/API slowness")
        
        if len(properties) > 100:
            print(f"   ⚠️  TOO MANY RESULTS: maxItems limit not working")
            print(f"      - Check options structure in API call")
            print(f"      - Verify actor supports maxItems parameter")
        
        if len(properties) == 0:
            print(f"   ❌ NO RESULTS: Possible issues:")
            print(f"      - Invalid city name")
            print(f"      - Date format issue")
            print(f"      - API token problem")
            print(f"      - Actor input format wrong")
        
        return duration, len(properties)
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"\n❌ AIRBNB SEARCH FAILED")
        print(f"⏱️  Duration: {duration:.1f} seconds") 
        print(f"🔥 Error: {str(e)}")
        print(f"📊 Error type: {type(e).__name__}")
        
        print(f"\n🔧 DEBUGGING HINTS:")
        print(f"   • Check APIFY_TOKEN environment variable")
        print(f"   • Verify actor name: tri_angle~new-fast-airbnb-scraper")
        print(f"   • Check input format matches actor requirements")
        print(f"   • Test with simpler parameters first")
        
        return duration, 0

if __name__ == "__main__":
    asyncio.run(debug_airbnb_single_city())