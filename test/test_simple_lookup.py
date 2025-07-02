# Simple test without imports
import re

def normalize_city_name(city: str) -> str:
    """Normalize city names for consistent matching"""
    city = city.lower().strip()
    
    # Handle German umlauts and special characters
    replacements = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ç': 'c', 'ñ': 'n'
    }
    
    for old, new in replacements.items():
        city = city.replace(old, new)
    
    # Remove special characters and normalize whitespace
    city = re.sub(r'[^\w\s]', '', city)
    city = re.sub(r'\s+', ' ', city).strip()
    
    return city

# Test the normalization
test_cases = [
    "Port de Soller",
    "Port de Sóller", 
    "Palma de Mallorca"
]

print("🧪 Testing Normalization:")
for case in test_cases:
    normalized = normalize_city_name(case)
    print(f"'{case}' → '{normalized}'")

# Test if our additions work
top_destinations_sample = {
    'port de soller': 'PMI',
    'soller': 'PMI',
    'palma de mallorca': 'PMI',
    'palma': 'PMI'
}

print("\n🧪 Testing Lookups:")
for case in test_cases:
    normalized = normalize_city_name(case)
    result = top_destinations_sample.get(normalized, "NOT FOUND")
    print(f"'{case}' → '{normalized}' → {result}")