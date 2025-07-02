# smart_city_lookup_simple.py - Simplified Smart City Lookup
from simple_city_resolver import resolve_city_to_iata
from typing import Optional, Tuple, List

async def hybrid_city_to_iata(city_input: str) -> Tuple[Optional[str], str, List[str]]:
    """
    Simplified Smart City Lookup:
    - Uses the simple resolver (no massive hardcoded dictionary)
    - Returns same interface for backward compatibility
    - Much cleaner and more maintainable
    
    Returns: (IATA_Code, Recognized_City, Suggestions)
    """
    if not city_input or not city_input.strip():
        return None, "", []
    
    print(f"🔍 Simple lookup: '{city_input}'")
    
    # Use the simple resolver
    iata_code = await resolve_city_to_iata(city_input)
    
    if iata_code:
        return iata_code, city_input.title(), []
    else:
        # If no result, provide some basic suggestions
        suggestions = _get_basic_suggestions(city_input)
        return None, city_input.title(), suggestions

def _get_basic_suggestions(city_input: str) -> List[str]:
    """Provide basic suggestions for failed lookups"""
    
    # Simple fuzzy matching against popular destinations
    popular_cities = [
        "Vienna", "Graz", "Salzburg", "Munich", "Berlin", "Frankfurt",
        "Paris", "London", "Barcelona", "Madrid", "Rome", "Milan",
        "Amsterdam", "Brussels", "Zurich", "Prague", "Budapest",
        "New York", "Dubai", "Bangkok", "Tokyo"
    ]
    
    from difflib import SequenceMatcher
    
    suggestions = []
    city_lower = city_input.lower()
    
    for city in popular_cities:
        similarity = SequenceMatcher(None, city_lower, city.lower()).ratio()
        
        # Boost score for partial matches
        if city_lower in city.lower() or city.lower() in city_lower:
            similarity = max(similarity, 0.7)
        
        if similarity > 0.5:
            suggestions.append(city)
    
    # Sort by similarity and return top 5
    suggestions.sort(key=lambda x: SequenceMatcher(None, city_lower, x.lower()).ratio(), reverse=True)
    return suggestions[:5]


# Backward compatibility alias
smart_city_to_iata = hybrid_city_to_iata


# Simple test
async def test_simplified_lookup():
    """Test the simplified lookup"""
    test_cases = [
        "Vienna",
        "Port de Soller", 
        "Deutschlandsberg",
        "VIE",
        "nonexistent city"
    ]
    
    print("🧪 Testing Simplified Lookup:")
    for city in test_cases:
        iata, recognized, suggestions = await hybrid_city_to_iata(city)
        print(f"  '{city}' → {iata or 'None'} ({recognized})")
        if suggestions:
            print(f"    💡 Suggestions: {', '.join(suggestions[:3])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_simplified_lookup())