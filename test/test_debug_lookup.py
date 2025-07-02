# Debug lookup for Port de Soller
from smart_city_lookup import normalize_city_name, check_top_destinations, CITY_ALIASES, TOP_DESTINATIONS

def test_port_soller_lookup():
    """Test the lookup steps for Port de Soller"""
    
    test_inputs = [
        "Port de Soller",
        "port de soller", 
        "Port de Sóller",
        "Palma de Mallorca",
        "Soller"
    ]
    
    print("🧪 Testing Port de Soller Lookup Steps:")
    print("=" * 50)
    
    for city_input in test_inputs:
        print(f"\n📍 Testing: '{city_input}'")
        
        # Step 1: Normalize
        normalized = normalize_city_name(city_input)
        print(f"   Normalized: '{normalized}'")
        
        # Step 2: Check TOP_DESTINATIONS
        direct_match = TOP_DESTINATIONS.get(normalized)
        print(f"   Direct match: {direct_match}")
        
        # Step 3: Check aliases
        alias_match = None
        if normalized in CITY_ALIASES:
            canonical = CITY_ALIASES[normalized]
            alias_match = TOP_DESTINATIONS.get(canonical)
            print(f"   Alias: '{normalized}' → '{canonical}' → {alias_match}")
        
        # Step 4: Check top destinations function
        top_dest_result = check_top_destinations(normalized)
        print(f"   Top destinations result: {top_dest_result}")
        
        print("-" * 30)

if __name__ == "__main__":
    test_port_soller_lookup()