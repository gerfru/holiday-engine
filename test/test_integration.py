# test_integration.py - Test the main.py integration
import asyncio

# Test the import to make sure it works
try:
    from smart_city_lookup_simple import hybrid_city_to_iata
    print("✅ Import successful: smart_city_lookup_simple")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)

async def test_integration():
    """Test the integrated resolver with realistic scenarios"""
    
    test_scenarios = [
        # Typical user inputs your app would receive
        ("Vienna", "VIE"),              # Common European city
        ("Graz", "GRZ"),                # Austrian city
        ("Port de Soller", "PMI"),      # Specific location that was problematic
        ("Barcelona", "BCN"),           # Popular destination
        ("VIE", "VIE"),                # User enters IATA directly
        ("New York", None),             # International (may not be in small airport db)
        ("Deutschlandsberg", "GRZ"),    # Small town → nearest airport
    ]
    
    print("🧪 Testing Integration Scenarios:")
    print("=" * 50)
    
    success_count = 0
    total_count = len(test_scenarios)
    
    for city_input, expected_iata in test_scenarios:
        print(f"\n📍 Testing: '{city_input}'")
        
        try:
            # Test the actual function that main.py uses
            result_iata, result_city, suggestions = await hybrid_city_to_iata(city_input)
            
            print(f"   Result: {result_iata or 'None'} (expected: {expected_iata or 'None'})")
            print(f"   City: {result_city}")
            
            if suggestions:
                print(f"   Suggestions: {', '.join(suggestions[:3])}")
            
            # Check if result matches expectation
            if expected_iata is None:
                # We expect it to either succeed or fail gracefully
                if result_iata:
                    print(f"   ✅ Found airport: {result_iata}")
                    success_count += 1
                else:
                    print(f"   ⚠️ No airport found (expected)")
                    success_count += 1
            else:
                # We expect a specific IATA code
                if result_iata == expected_iata:
                    print(f"   ✅ Correct result")
                    success_count += 1
                else:
                    print(f"   ❌ Unexpected result")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("-" * 30)
    
    print(f"\n📊 Results: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 All tests passed! Integration ready.")
    else:
        print("⚠️ Some tests failed. Review needed.")

async def test_performance():
    """Quick performance test"""
    import time
    
    print("\n⚡ Performance Test:")
    print("=" * 30)
    
    # Test repeated lookups (should hit cache)
    test_city = "Vienna"
    iterations = 10
    
    start_time = time.time()
    
    for i in range(iterations):
        await hybrid_city_to_iata(test_city)
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations * 1000
    
    print(f"Average lookup time: {avg_time:.2f}ms ({iterations} iterations)")
    print(f"Expected: <10ms for cached lookups")

if __name__ == "__main__":
    async def run_tests():
        await test_integration()
        await test_performance()
    
    asyncio.run(run_tests())