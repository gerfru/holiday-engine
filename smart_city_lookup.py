# smart_city_lookup.py - Hybrid Airport Lookup System
import asyncio
import httpx
import re
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, Dict

# TOP DESTINATIONS - Hardcoded für 99% der Nutzer (inkl. Graz!)
TOP_DESTINATIONS = {
    # Österreich
    'wien': 'VIE',
    'vienna': 'VIE', 
    'graz': 'GRZ',  # 🆕 Hinzugefügt!
    'salzburg': 'SZG',
    'linz': 'LNZ',
    'innsbruck': 'INN',
    'klagenfurt': 'KLU',
    
    # Deutschland  
    'münchen': 'MUC',
    'munich': 'MUC',
    'berlin': 'BER',
    'hamburg': 'HAM',
    'düsseldorf': 'DUS',
    'frankfurt': 'FRA',
    'stuttgart': 'STR',
    'köln': 'CGN',
    'cologne': 'CGN',
    'hannover': 'HAJ',
    'nürnberg': 'NUE',
    'nuremberg': 'NUE',
    'leipzig': 'LEJ',
    'dresden': 'DRS',
    'bremen': 'BRE',
    
    # Europa Highlights
    'barcelona': 'BCN',
    'rom': 'FCO',
    'rome': 'FCO',
    'paris': 'CDG',
    'london': 'LHR',
    'amsterdam': 'AMS',
    'madrid': 'MAD',
    'lisboa': 'LIS',
    'lisbon': 'LIS',
    'milano': 'MXP',
    'milan': 'MXP',
    'mailand': 'MXP',
    'venedig': 'VCE',
    'venice': 'VCE',
    'florenz': 'FLR',
    'florence': 'FLR',
    'athen': 'ATH',
    'athens': 'ATH',
    'istanbul': 'IST',
    'stockholm': 'ARN',
    'oslo': 'OSL',
    'kopenhagen': 'CPH',
    'copenhagen': 'CPH',
    'helsinki': 'HEL',
    'prag': 'PRG',
    'prague': 'PRG',
    'budapest': 'BUD',
    'mallorca': 'PMI',
    'palma': 'PMI',
    'ibiza': 'IBZ',
    'canary islands': 'LPA',
    'las palmas': 'LPA',
    'tenerife': 'TFS',
    'cyprus': 'LCA',
    'nicosia': 'LCA',
    'larnaca': 'LCA',
    'crete': 'HER',
    'heraklion': 'HER',
    'santorini': 'JTR',
    'mykonos': 'JMK',
    'rhodes': 'RHO',
    'corfu': 'CFU',
    'nice': 'NCE',
    'nizza': 'NCE',
    'lyon': 'LYS',
    'marseille': 'MRS',
    'toulouse': 'TLS',
    'bordeaux': 'BOD',
    'strasbourg': 'SXB',
    'brussels': 'BRU',
    'brüssel': 'BRU',
    'antwerp': 'ANR',
    'antwerpen': 'ANR',
    'geneva': 'GVA',
    'genf': 'GVA',
    'basel': 'BSL',
    'bern': 'BRN',
    'zurich': 'ZUR',
    'zürich': 'ZUR',
    'edinburgh': 'EDI',
    'glasgow': 'GLA',
    'manchester': 'MAN',
    'birmingham': 'BHX',
    'dublin': 'DUB',
    'cork': 'ORK',
    'reykjavik': 'KEF',
    'lisbon': 'LIS',
    'lisboa': 'LIS',
    'porto': 'OPO',
    'seville': 'SVQ',
    'sevilla': 'SVQ',
    'valencia': 'VLC',
    'bilbao': 'BIO',
    'naples': 'NAP',
    'neapel': 'NAP',
    'turin': 'TRN',
    'bologna': 'BLQ',
    'catania': 'CTA',
    'palermo': 'PMO',
    'bari': 'BRI',
    'genoa': 'GOA',
    'genua': 'GOA',
    'warsaw': 'WAW',
    'warschau': 'WAW',
    'krakow': 'KRK',
    'krakau': 'KRK',
    'gdansk': 'GDN',
    'danzig': 'GDN',
    'bucharest': 'OTP',
    'bukarest': 'OTP',
    'belgrade': 'BEG',
    'belgrad': 'BEG',
    'zagreb': 'ZAG',
    'split': 'SPU',
    'dubrovnik': 'DBV',
    'ljubljana': 'LJU',
    'bratislava': 'BTS',
    'riga': 'RIX',
    'tallinn': 'TLL',
    'vilnius': 'VNO',
    'moscow': 'SVO',
    'moskau': 'SVO',
    'st petersburg': 'LED',
    'sankt petersburg': 'LED',
    'kiev': 'KBP',
    'kiew': 'KBP',
    'kyiv': 'KBP',
    'minsk': 'MSQ',
    'sofia': 'SOF',
    'thessaloniki': 'SKG',
    
    # USA & Canada
    'new york': 'JFK',
    'nyc': 'JFK',
    'los angeles': 'LAX',
    'la': 'LAX',
    'chicago': 'ORD',
    'miami': 'MIA',
    'san francisco': 'SFO',
    'sf': 'SFO',
    'las vegas': 'LAS',
    'vegas': 'LAS',
    'seattle': 'SEA',
    'boston': 'BOS',
    'washington': 'DCA',
    'dc': 'DCA',
    'philadelphia': 'PHL',
    'atlanta': 'ATL',
    'denver': 'DEN',
    'phoenix': 'PHX',
    'dallas': 'DFW',
    'houston': 'IAH',
    'orlando': 'MCO',
    'tampa': 'TPA',
    'detroit': 'DTW',
    'minneapolis': 'MSP',
    'cleveland': 'CLE',
    'pittsburgh': 'PIT',
    'portland': 'PDX',
    'san diego': 'SAN',
    'salt lake city': 'SLC',
    'toronto': 'YYZ',
    'vancouver': 'YVR',
    'montreal': 'YUL',
    'calgary': 'YYC',
    
    # Asia
    'tokyo': 'NRT',
    'osaka': 'KIX',
    'kyoto': 'KIX',
    'nagoya': 'NGO',
    'sapporo': 'CTS',
    'seoul': 'ICN',
    'busan': 'PUS',
    'beijing': 'PEK',
    'peking': 'PEK',
    'shanghai': 'PVG',
    'guangzhou': 'CAN',
    'shenzhen': 'SZX',
    'hong kong': 'HKG',
    'hongkong': 'HKG',
    'taipei': 'TPE',
    'manila': 'MNL',
    'bangkok': 'BKK',
    'phuket': 'HKT',
    'singapore': 'SIN',
    'singapur': 'SIN',
    'kuala lumpur': 'KUL',
    'jakarta': 'CGK',
    'bali': 'DPS',
    'denpasar': 'DPS',
    'ho chi minh': 'SGN',
    'saigon': 'SGN',
    'hanoi': 'HAN',
    'mumbai': 'BOM',
    'bombay': 'BOM',
    'delhi': 'DEL',
    'new delhi': 'DEL',
    'bangalore': 'BLR',
    'chennai': 'MAA',
    'madras': 'MAA',
    'kolkata': 'CCU',
    'calcutta': 'CCU',
    'hyderabad': 'HYD',
    'goa': 'GOI',
    'cochin': 'COK',
    'kochi': 'COK',
    'colombo': 'CMB',
    'kathmandu': 'KTM',
    'dhaka': 'DAC',
    'islamabad': 'ISB',
    'karachi': 'KHI',
    'lahore': 'LHE',
    'kabul': 'KBL',
    'tashkent': 'TAS',
    'almaty': 'ALA',
    'astana': 'NUR',
    'nur-sultan': 'NUR',
    'tbilisi': 'TBS',
    'yerevan': 'EVN',
    'baku': 'GYD',
    'tehran': 'IKA',
    'teheran': 'IKA',
    
    # Middle East & Africa
    'dubai': 'DXB',
    'abu dhabi': 'AUH',
    'doha': 'DOH',
    'kuwait': 'KWI',
    'riyadh': 'RUH',
    'jeddah': 'JED',
    'medina': 'MED',
    'muscat': 'MCT',
    'beirut': 'BEY',
    'damascus': 'DAM',
    'amman': 'AMM',
    'tel aviv': 'TLV',
    'jerusalem': 'JRS',
    'cairo': 'CAI',
    'kairo': 'CAI',
    'casablanca': 'CMN',
    'marrakech': 'RAK',
    'marrakesh': 'RAK',
    'tunis': 'TUN',
    'algiers': 'ALG',
    'algier': 'ALG',
    'tripoli': 'TIP',
    'addis ababa': 'ADD',
    'nairobi': 'NBO',
    'dar es salaam': 'DAR',
    'cape town': 'CPT',
    'kapstadt': 'CPT',
    'johannesburg': 'JNB',
    'durban': 'DUR',
    
    # Oceania
    'sydney': 'SYD',
    'melbourne': 'MEL',
    'brisbane': 'BNE',
    'perth': 'PER',
    'adelaide': 'ADL',
    'darwin': 'DRW',
    'auckland': 'AKL',
    'wellington': 'WLG',
    'christchurch': 'CHC',
    'queenstown': 'ZQN',
    'suva': 'SUV',
    'nadi': 'NAN',
    'port moresby': 'POM',
    'noumea': 'NOU',
    'papeete': 'PPT',
    'tahiti': 'PPT'
}

# Aliases für verschiedene Schreibweisen
CITY_ALIASES = {
    'muenchen': 'münchen',
    'duesseldorf': 'düsseldorf', 
    'koeln': 'köln',
    'nuernberg': 'nürnberg',
    'ny': 'new york',
    'nyc': 'new york',
    'la': 'los angeles',
    'sf': 'san francisco',
    'lon': 'london',
    'par': 'paris',
    'bcn': 'barcelona',
    'mad': 'madrid',
    'muc': 'münchen',
    'vie': 'wien',
    'grz': 'graz',  # 🆕 Alias für Graz
    'fco': 'rom',
    'cdg': 'paris',
    'lhr': 'london'
}

async def hybrid_city_to_iata(city_input: str) -> Tuple[Optional[str], str, List[str]]:
    """
    Hybrid Airport Lookup:
    1. Prüfe Top Destinations (hardcoded) 
    2. Falls nicht gefunden → Airport API
    3. Falls API fehlt → Fuzzy Suggestions
    
    Returns: (IATA_Code, Erkannte_Stadt, Vorschläge)
    """
    
    if not city_input or not city_input.strip():
        return None, "", []
    
    # Normalisiere Input
    normalized = normalize_city_name(city_input)
    original_input = city_input.title()
    
    print(f"🔍 Hybrid Lookup: '{city_input}' → '{normalized}'")
    
    # STEP 1: Check Top Destinations (Fast Path - 99% Coverage)
    iata_code = check_top_destinations(normalized)
    if iata_code:
        city_name = get_canonical_city_name(normalized)
        print(f"✅ Top Destination Match: {city_name} → {iata_code}")
        return iata_code, city_name, []
    
    # STEP 2: Check if it's already an IATA code
    if len(normalized) == 3 and normalized.isalpha():
        potential_iata = normalized.upper()
        print(f"🔍 Checking if '{potential_iata}' is valid IATA code...")
        
        # Validate IATA (simplified - could use real API validation)
        if is_valid_iata_format(potential_iata):
            print(f"✅ Valid IATA format: {potential_iata}")
            return potential_iata, potential_iata, []
    
    # STEP 3: Airport API Lookup (Fallback for unknown cities)
    print(f"🌐 Searching Airport API for: {city_input}")
    api_result = await search_airport_api(city_input)
    if api_result:
        print(f"✅ Airport API Match: {api_result['city']} → {api_result['iata']}")
        return api_result['iata'], api_result['city'], []
    
    # STEP 4: Fuzzy Suggestions from Top Destinations
    print(f"🔍 Finding fuzzy matches for: {normalized}")
    suggestions = find_fuzzy_matches(normalized)
    
    if suggestions:
        print(f"💡 Suggestions: {[s['city'] for s in suggestions[:3]]}")
        return None, original_input, [s['city'] for s in suggestions[:5]]
    
    print(f"❌ No matches found for: {city_input}")
    return None, original_input, []

def check_top_destinations(normalized_city: str) -> Optional[str]:
    """Check hardcoded top destinations"""
    
    # Direct match
    if normalized_city in TOP_DESTINATIONS:
        return TOP_DESTINATIONS[normalized_city]
    
    # Check aliases
    if normalized_city in CITY_ALIASES:
        canonical = CITY_ALIASES[normalized_city]
        if canonical in TOP_DESTINATIONS:
            return TOP_DESTINATIONS[canonical]
    
    return None

def get_canonical_city_name(normalized_city: str) -> str:
    """Get the canonical display name for a city"""
    
    # Map back to nice display names
    display_names = {
        'wien': 'Wien',
        'graz': 'Graz',
        'salzburg': 'Salzburg', 
        'linz': 'Linz',
        'innsbruck': 'Innsbruck',
        'münchen': 'München',
        'berlin': 'Berlin',
        'barcelona': 'Barcelona',
        'rom': 'Rom',
        'paris': 'Paris',
        'london': 'London',
        'amsterdam': 'Amsterdam',
        'madrid': 'Madrid',
        'new york': 'New York',
        'los angeles': 'Los Angeles',
        'tokyo': 'Tokyo',
        'dubai': 'Dubai',
        'mallorca': 'Mallorca',
        'palma': 'Palma',
        'ibiza': 'Ibiza',
        'nice': 'Nice',
        'brussels': 'Brussels',
        'geneva': 'Geneva',
        'zurich': 'Zurich',
        'dublin': 'Dublin',
        'lisbon': 'Lisbon',
        'porto': 'Porto',
        'valencia': 'Valencia',
        'naples': 'Naples',
        'warsaw': 'Warsaw',
        'krakow': 'Krakow',
        'bucharest': 'Bucharest',
        'prague': 'Prague',
        'budapest': 'Budapest',
        'zagreb': 'Zagreb',
        'split': 'Split',
        'dubrovnik': 'Dubrovnik',
        'moscow': 'Moscow',
        'st petersburg': 'St Petersburg',
        'sofia': 'Sofia',
        'thessaloniki': 'Thessaloniki',
        'santorini': 'Santorini',
        'mykonos': 'Mykonos',
        'crete': 'Crete',
        'rhodes': 'Rhodes',
        'cyprus': 'Cyprus',
        'reykjavik': 'Reykjavik',
        'san francisco': 'San Francisco',
        'las vegas': 'Las Vegas',
        'seattle': 'Seattle',
        'boston': 'Boston',
        'washington': 'Washington DC',
        'atlanta': 'Atlanta',
        'miami': 'Miami',
        'orlando': 'Orlando',
        'chicago': 'Chicago',
        'toronto': 'Toronto',
        'vancouver': 'Vancouver',
        'osaka': 'Osaka',
        'seoul': 'Seoul',
        'beijing': 'Beijing',
        'shanghai': 'Shanghai',
        'hong kong': 'Hong Kong',
        'taipei': 'Taipei',
        'bangkok': 'Bangkok',
        'singapore': 'Singapore',
        'kuala lumpur': 'Kuala Lumpur',
        'bali': 'Bali',
        'mumbai': 'Mumbai',
        'delhi': 'Delhi',
        'sydney': 'Sydney',
        'melbourne': 'Melbourne',
        'auckland': 'Auckland',
        'tel aviv': 'Tel Aviv',
        'cairo': 'Cairo',
        'casablanca': 'Casablanca',
        'cape town': 'Cape Town',
        'johannesburg': 'Johannesburg'
    }
    
    # Check aliases first
    canonical = CITY_ALIASES.get(normalized_city, normalized_city)
    
    # Return display name or title case
    return display_names.get(canonical, canonical.title())

async def search_airport_api(city: str) -> Optional[Dict]:
    """
    Search external Airport API for unknown cities
    Currently uses a mock - could integrate real APIs like:
    - Amadeus API
    - IATA Airport Database
    - OpenFlights Database
    """
    
    try:
        # MOCK: Simulate API call for demonstration
        print(f"📡 [MOCK] Airport API Call for: {city}")
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Mock database of additional airports
        mock_airports = {
            'klagenfurt': {'iata': 'KLU', 'city': 'Klagenfurt'},
            'basel': {'iata': 'BSL', 'city': 'Basel'},
            'geneva': {'iata': 'GVA', 'city': 'Geneva'},
            'genf': {'iata': 'GVA', 'city': 'Genf'},
            'zurich': {'iata': 'ZUR', 'city': 'Zurich'},
            'zürich': {'iata': 'ZUR', 'city': 'Zürich'},
            'bern': {'iata': 'BRN', 'city': 'Bern'},
            'nice': {'iata': 'NCE', 'city': 'Nice'},
            'nizza': {'iata': 'NCE', 'city': 'Nizza'},
            'lyon': {'iata': 'LYS', 'city': 'Lyon'},
            'marseille': {'iata': 'MRS', 'city': 'Marseille'},
            'toulouse': {'iata': 'TLS', 'city': 'Toulouse'},
            'brussels': {'iata': 'BRU', 'city': 'Brussels'},
            'brüssel': {'iata': 'BRU', 'city': 'Brüssel'},
        }
        
        normalized = normalize_city_name(city)
        if normalized in mock_airports:
            return mock_airports[normalized]
        
        # TODO: Implement real Airport API
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"https://api.amadeus.com/v1/reference-data/locations?keyword={city}")
        #     return parse_amadeus_response(response.json())
        
        return None
        
    except Exception as e:
        print(f"❌ Airport API Error: {e}")
        return None

def normalize_city_name(city: str) -> str:
    """Normalize city names for consistent matching"""
    
    # Convert to lowercase
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

def find_fuzzy_matches(query: str) -> List[Dict]:
    """Find similar cities using fuzzy matching"""
    
    results = []
    
    # Search in top destinations
    for city in TOP_DESTINATIONS.keys():
        similarity = SequenceMatcher(None, query, city).ratio()
        
        # Boost score for partial matches
        if query in city or city in query:
            similarity = max(similarity, 0.7)
        
        # Boost score for prefix matches
        if city.startswith(query) or query.startswith(city):
            similarity = max(similarity, 0.8)
        
        if similarity > 0.5:  # Minimum similarity threshold
            results.append({
                'city': get_canonical_city_name(city),
                'score': similarity,
                'iata': TOP_DESTINATIONS[city]
            })
    
    # Sort by similarity score
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def is_valid_iata_format(code: str) -> bool:
    """Check if a 3-letter code could be a valid IATA airport code"""
    
    # Basic format validation
    if len(code) != 3 or not code.isalpha():
        return False
    
    # List of known valid IATA codes (subset)
    known_iata_codes = {
        'VIE', 'GRZ', 'SZG', 'LNZ', 'INN', 'KLU',  # Austria
        'MUC', 'BER', 'HAM', 'DUS', 'FRA', 'STR', 'CGN',  # Germany
        'BCN', 'FCO', 'CDG', 'LHR', 'AMS', 'MAD',  # Europe
        'JFK', 'LAX', 'ORD', 'NRT', 'BKK', 'SIN', 'DXB'  # International
    }
    
    return code.upper() in known_iata_codes

def get_popular_destinations_with_graz() -> List[Dict]:
    """Get popular destinations including Graz for autocomplete"""
    
    popular = [
        {'city': 'Wien', 'iata': 'VIE', 'country': '🇦🇹'},
        {'city': 'Graz', 'iata': 'GRZ', 'country': '🇦🇹'},  # 🆕 Graz prominent!
        {'city': 'Salzburg', 'iata': 'SZG', 'country': '🇦🇹'},
        {'city': 'München', 'iata': 'MUC', 'country': '🇩🇪'},
        {'city': 'Berlin', 'iata': 'BER', 'country': '🇩🇪'},
        {'city': 'Barcelona', 'iata': 'BCN', 'country': '🇪🇸'},
        {'city': 'Rom', 'iata': 'FCO', 'country': '🇮🇹'},
        {'city': 'Paris', 'iata': 'CDG', 'country': '🇫🇷'},
        {'city': 'London', 'iata': 'LHR', 'country': '🇬🇧'},
        {'city': 'Amsterdam', 'iata': 'AMS', 'country': '🇳🇱'},
        {'city': 'Madrid', 'iata': 'MAD', 'country': '🇪🇸'},
        {'city': 'New York', 'iata': 'JFK', 'country': '🇺🇸'},
        {'city': 'Tokyo', 'iata': 'NRT', 'country': '🇯🇵'},
        {'city': 'Dubai', 'iata': 'DXB', 'country': '🇦🇪'},
        {'city': 'Ibiza', 'iata': 'IBZ', 'country': '🇪🇸'},
        {'city': 'Nice', 'iata': 'NCE', 'country': '🇫🇷'},
        {'city': 'Santorini', 'iata': 'JTR', 'country': '🇬🇷'},
        {'city': 'Las Vegas', 'iata': 'LAS', 'country': '🇺🇸'},
        {'city': 'San Francisco', 'iata': 'SFO', 'country': '🇺🇸'},
        {'city': 'Miami', 'iata': 'MIA', 'country': '🇺🇸'},
        {'city': 'Bangkok', 'iata': 'BKK', 'country': '🇹🇭'},
        {'city': 'Singapore', 'iata': 'SIN', 'country': '🇸🇬'},
        {'city': 'Hong Kong', 'iata': 'HKG', 'country': '🇭🇰'},
        {'city': 'Sydney', 'iata': 'SYD', 'country': '🇦🇺'},
        {'city': 'Bali', 'iata': 'DPS', 'country': '🇮🇩'}
    ]
    
    return popular

# Alias for backward compatibility
smart_city_to_iata = hybrid_city_to_iata

# Test function
async def test_hybrid_lookup():
    """Test the hybrid lookup system"""
    test_cases = [
        "Wien", "Graz", "barcelona", "new york", "münchen",  # Top destinations
        "ZUR", "GVA", "NCE",  # IATA codes  
        "zürich", "genf", "nizza",  # API fallback
        "munih", "barcellona", "viena"  # Fuzzy matches
    ]
    
    print("🧪 Testing Hybrid City Lookup:")
    for city in test_cases:
        iata, recognized, suggestions = await hybrid_city_to_iata(city)
        print(f"  '{city}' → {iata or 'None'} ({recognized})")
        if suggestions:
            print(f"    💡 Suggestions: {', '.join(suggestions[:3])}")

if __name__ == "__main__":
    asyncio.run(test_hybrid_lookup())