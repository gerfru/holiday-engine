# Software Design Specification: Holiday Engine

**Version:** 2.0.0
**Date:** July 3, 2025
**Author:** Development Team
**Status:** Active Development

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture Design](#3-architecture-design)
4. [Component Specifications](#4-component-specifications)
5. [Data Models](#5-data-models)
6. [API Design](#6-api-design)
7. [User Interface Design](#7-user-interface-design)
8. [Development Guidelines](#8-development-guidelines)

---

## 1. Executive Summary

### 1.1 Project Overview

Holiday Engine is a travel search and comparison platform that combines flight and accommodation data from multiple sources to provide intelligent travel recommendations. The system uses a service-oriented architecture with real-time city autocomplete, advanced geocoding, and intelligent combination scoring.

### 1.2 Key Features (Implemented)

- **Multi-Source Data Integration**: Flights (Skyscanner), Hotels (Booking.com), Vacation Rentals (Airbnb)
- **Live City Autocomplete**: Real-time city suggestions using OpenStreetMap Nominatim
- **Intelligent Combination Engine**: Scoring algorithm for optimal travel packages
- **Advanced Geocoding**: Real airport database with distance-based matching
- **Concurrent Search Processing**: Parallel API calls for optimal performance
- **CSV Export**: Search result analysis and data export

### 1.3 Technical Stack

- **Backend**: Python 3.12+, FastAPI, Uvicorn
- **Data Processing**: Pandas, Geopy
- **External APIs**: Apify (travel data), OpenStreetMap Nominatim (geocoding)
- **Configuration**: Pydantic Settings, Environment Variables
- **Testing**: Custom test suite with multiple test categories
- **Frontend**: Vanilla JavaScript, HTML5, CSS3

---

## 2. System Overview

### 2.1 System Context

```
               ┌─────────────────┐    ┌─────────────────┐
               │   Web Browser   │    │  Mobile Client  │
               └─────────┬───────┘    └─────────┬───────┘
                         │                      │
                         └──────────────────────
                                  │
                    ┌─────────────▼─────────────┐
                    │     Holiday Engine        │
                    │    (FastAPI Server)       │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼────────────────────────┐
          │                      │                        │
     ┌────▼────┐           ┌─────▼───────┐         ┌──────▼──────┐
     │  Apify  │           │OpenStreetMap│         │  Airport DB │
     │   API   │           │  Nominatim  │         │   (Local)   │
     └─────────┘           └─────────────┘         └─────────────┘
```

### 2.2 Core Capabilities

1. **Search Orchestration**: Coordinate multiple search operations
2. **Data Aggregation**: Combine results from heterogeneous sources
3. **Intelligent Ranking**: Score and rank travel combinations
4. **Real-time Autocomplete**: Provide instant city suggestions
5. **Geographic Resolution**: Convert city names to airport codes
6. **Result Export**: Generate analytical reports in CSV format

### 2.3 Quality Attributes

- **Performance**: Sub-3-second search response times
- **Reliability**: Graceful degradation with mock data fallbacks
- **Scalability**: Async/concurrent processing
- **Maintainability**: Modular architecture with clear separation of concerns
- **Usability**: Live autocomplete and intuitive three-tab interface

---

## 3. Architecture Design

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  Templates/     │  Static Assets  │  REST API      │            │
│  (Jinja2)       │  (CSS/JS)       │  Endpoints     │            │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                         Application Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  Route Handlers │  Validation    │  Error Handling │            │
│  (FastAPI)      │  (Manual)      │  (Custom)       │            │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌──────────────────────────────────────────────────────────────────┐
│                          Business Layer                          │
├──────────────────────────────────────────────────────────────────┤
│  Combination    │  Search        │  City Resolution│  CSV Export │
│  Engine         │  Orchestration │  Service        │  Engine     │
└──────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                          Service Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  Flight         │  Hotel         │  Airbnb        │  Geocoding  │
│  Service        │  Service       │  Service       │  Service    │
└─────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                         Infrastructure Layer                    │
├─────────────────────────────────────────────────────────────────┤
│  API Client     │  Data Parsers  │  Configuration │  Logging    │
│  (HTTP/Retry)   │  (JSON/CSV)    │  (Settings)    │  (Basic)    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Architecture

#### 3.2.1 Core Services

- **Flight Service**: Manages flight search operations via Skyscanner API
- **Hotel Service**: Handles hotel search through Booking.com API
- **Airbnb Service**: Processes vacation rental search via Airbnb API
- **City Resolver Service**: Geocodes cities and finds nearest airports
- **Combination Engine**: Creates and scores travel packages

#### 3.2.2 Utility Services

- **API Client**: Unified HTTP client with retry logic
- **Data Parsers**: Transform external API responses to internal models
- **Configuration Service**: Centralized settings management
- **CSV Export**: Generate reports and export functionality

### 3.3 Data Flow Architecture

```
User Request → Input Validation → City Resolution → Concurrent Search
     ↓                ↓                ↓                    ↓
Search Params → Manual Validation → IATA Codes → [Flight|Hotel|Airbnb] APIs
     ↓                ↓                ↓                    ↓
Combination Engine ← Data Parsers ← Raw API Data ← HTTP Responses
     ↓                ↓                ↓                    ↓
Scoring Algorithm → Ranked Results → Template Rendering → User Response
```

---

## 4. Component Specifications

### 4.1 Main Application (`main.py`)

#### 4.1.1 Responsibilities

- HTTP server initialization and configuration
- Route definitions and request handling
- Template rendering and response formatting
- Error handling and exception management
- Health check and monitoring endpoints

#### 4.1.2 Key Components

```python
class FastAPIApplication:
    - app: FastAPI instance
    - templates: Jinja2Templates
    - services: Service container
  
    Methods:
    - startup_event(): Application initialization
    - health_check(): System health monitoring
    - smart_search(): Main search orchestration
    - city_autocomplete(): Live city suggestions
    - city_resolve(): IATA code resolution
```

#### 4.1.3 Route Specifications

| Route                        | Method | Purpose          | Parameters                         |
| ---------------------------- | ------ | ---------------- | ---------------------------------- |
| `/`                        | GET    | Home page        | None                               |
| `/smart-search`            | POST   | Main search      | origin, destination, dates, budget |
| `/api/cities/autocomplete` | GET    | City suggestions | q (query string)                   |
| `/api/cities/resolve`      | GET    | City to IATA     | city (city name)                   |
| `/health`                  | GET    | Health check     | None                               |
| `/test-flights`            | POST   | Flight testing   | origin, destination, date          |
| `/test-hotels`             | POST   | Hotel testing    | city, checkin, checkout            |

### 4.2 Business Logic (`business_logic.py`)

#### 4.2.1 TravelCombinationEngine

```python
class TravelCombinationEngine:
    def create_combinations(
        outbound_flights: List[Flight],
        return_flights: List[Flight],
        hotels: List[Hotel],
        airbnb_properties: List[Airbnb],
        search_params: SearchParams
    ) -> List[TravelCombination]:
        """
        Creates intelligent travel combinations using scoring algorithm
      
        Algorithm:
        1. Prepare accommodation options (hotels + airbnb)
        2. Generate all possible combinations (flights + accommodations)
        3. Filter by budget constraints (with 20% flexibility)
        4. Score combinations using multi-factor algorithm
        5. Return top 5 ranked combinations
        """
```

#### 4.2.2 Scoring Algorithm

```python
def calculate_combination_score(
    total_cost: float,
    accommodation_rating: float,
    budget: Optional[int]
) -> float:
    """
    Multi-factor scoring algorithm:
    - Accommodation Rating: 0-50 points (rating * 10)
    - Budget Compliance: 0-50 points
      - Under 80% budget: 50 points
      - Within budget: 30 points
      - Up to 10% over: 15 points
      - Over 10%: 0 points
    - Total Score: 0-100 points
    """
```

### 4.3 Configuration Management (`config/settings.py`)

#### 4.3.1 Settings Class

```python
class Settings(BaseSettings):
    # API Configuration
    apify_token: Optional[str] = None
    x_rapidapi_key: Optional[str] = None
  
    # Application Configuration
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
  
    # Performance Configuration
    max_retries: int = 3
    base_retry_delay: float = 2.0
    max_retry_delay: float = 60.0
    api_timeout: float = 300.0
  
    # Search Limits
    max_flights_per_search: int = 50
    max_hotels_per_search: int = 200
    max_airbnb_per_search: int = 100
    max_combinations: int = 5
  
    # Output Configuration
    output_directory: str = "output"
    export_csv: bool = True
```

### 4.4 Service Layer

#### 4.4.1 Flight Service (`services/flight_service.py`)

```python
class FlightService:
    def __init__(self, api_client: ApifyClient):
        self.api_client = api_client
        self.parser = FlightParser()
  
    async def search_flights(
        origin: str,
        destination: str,
        date: str,
        max_results: int = 10
    ) -> List[Flight]:
        """Search flights using Skyscanner via Apify"""
  
    async def search_round_trip(
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        max_results_per_direction: int = 25
    ) -> Dict[str, List[Flight]]:
        """Search round-trip flights concurrently"""
```

#### 4.4.2 Hotel Service (`services/hotel_service.py`)

```python
class AccommodationService:
    def __init__(self, api_client: ApifyClient):
        self.api_client = api_client
        self.hotel_parser = HotelParser()
        self.airbnb_parser = AirbnbParser()
  
    async def search_hotels(...) -> List[Hotel]:
        """Search hotels via Booking.com"""
  
    async def search_airbnb(...) -> List[Airbnb]:
        """Search Airbnb properties"""
  
    async def search_all_accommodations(...) -> Dict[str, List]:
        """Search all accommodation types concurrently"""
```

#### 4.4.3 City Resolver Service (`services/city_resolver.py`)

```python
class CityResolverService:
    def __init__(self):
        self.cache = {}
        self.airports_df = None  # Real airport database
        self.common_cities = self._load_common_cities()
        self.geolocator = Nominatim(user_agent="HolidayEngine/2.0")
  
    async def resolve_to_iata(
        location: str
    ) -> Tuple[Optional[str], str, List[str]]:
        """
        Multi-step resolution process:
        1. Cache lookup (fast path)
        2. Common cities (curated quality)
        3. Direct IATA code validation
        4. Geocoding + nearest airport calculation
        5. Suggestion generation for failed lookups
        """
```

### 4.5 Infrastructure Layer

#### 4.5.1 API Client (`utils/api_client.py`)

```python
class ApifyClient:
    def __init__(self, api_token: str, retry_config: RetryConfig):
        self.api_token = api_token
        self.retry_config = retry_config
        self.base_url = "https://api.apify.com/v2/acts"
  
    async def call_actor(
        actor_name: str,
        input_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Robust API calling with:
        - Exponential backoff retry logic
        - Request/response logging
        - Error classification and handling
        """
```

#### 4.5.2 Data Parsers (`utils/data_parser.py`)

```python
class FlightParser:
    def parse_flights(self, raw_data: List[Dict]) -> List[Flight]:
        """Parse Skyscanner API response"""

class HotelParser:
    def parse_hotels(self, raw_data: List[Dict]) -> List[Hotel]:
        """Parse Booking.com API response"""

class AirbnbParser:
    def parse_airbnb(self, raw_data: List[Dict]) -> List[Airbnb]:
        """Parse Airbnb API response"""
```

---

## 5. Data Models

### 5.1 Core Domain Models

#### 5.1.1 Flight Model

```python
@dataclass
class Flight:
    airline: str
    flight_number: Optional[str]
    departure_time: str
    arrival_time: str
    duration: str
    stops: int
    price: float
    currency: str
    origin: str
    destination: str
    date: str
    source: str
    booking_url: str
  
    # Derived properties
    @property
    def is_direct(self) -> bool:
        return self.stops == 0
```

#### 5.1.2 Hotel Model

```python
@dataclass
class Hotel:
    name: str
    rating: float
    review_count: Optional[int]
    location: str
    price_per_night: float
    currency: str
    room_type: Optional[str]
    amenities: List[str]
    source: str
    booking_url: str
  
    # Derived properties
    @property
    def price_rating_ratio(self) -> float:
        return self.price_per_night / max(self.rating, 1.0)
```

#### 5.1.3 Airbnb Model

```python
@dataclass
class Airbnb:
    name: str
    property_type: str
    rating: float
    review_count: Optional[int]
    location: str
    person_capacity: int
    price_per_night: float
    currency: str
    badges: List[str]
    amenities: List[str]
    source: str
    booking_url: str
  
    # Derived properties
    @property
    def price_per_person(self) -> float:
        return self.price_per_night / max(self.person_capacity, 1)
```

#### 5.1.4 Travel Combination Model

```python
@dataclass
class TravelCombination:
    outbound_flight: Flight
    return_flight: Flight
    accommodation: Union[Hotel, Airbnb]
    accommodation_type: str
  
    # Cost breakdown
    flight_cost: float
    accommodation_cost: float
    total_cost: float
  
    # Trip details
    nights: int
    persons: int
  
    # Scoring
    score: float
    cost_per_person: float
    cost_per_night: float
```

### 5.2 Configuration Models

#### 5.2.1 Search Parameters

```python
@dataclass
class SearchParams:
    origin: str
    destination: str
    departure_date: str
    return_date: str
    persons: int
    budget: Optional[int] = None
  
    # Derived properties
    @property
    def nights(self) -> int:
        dep = datetime.strptime(self.departure_date, '%Y-%m-%d')
        ret = datetime.strptime(self.return_date, '%Y-%m-%d')
        return (ret - dep).days
```

---

## 6. API Design

### 6.1 REST API Endpoints

#### 6.1.1 Search Endpoints

**POST /smart-search**

- **Purpose**: Main travel search endpoint
- **Request Body**: Form data with search parameters
- **Response**: HTML template with search results

```python
# Request Parameters
origin: str          # Origin city name or IATA code
destination: str     # Destination city name or IATA code
departure: str       # Departure date (YYYY-MM-DD)
return_date: str     # Return date (YYYY-MM-DD)
budget: Optional[int] # Budget in EUR
persons: int         # Number of travelers (1-10)
```

#### 6.1.2 Autocomplete Endpoints

**GET /api/cities/autocomplete**

- **Purpose**: Live city name suggestions
- **Parameters**: `q` (query string, min 2 characters)
- **Response**: JSON with city suggestions

```python
# Response Format
{
    "suggestions": [
        {
            "city": "Barcelona",
            "country": "Spain",
            "country_code": "ES",
            "display_name": "Barcelona, Spain",
            "lat": 41.3851,
            "lon": 2.1734,
            "importance": 0.8,
            "type": "city"
        }
    ]
}
```

**GET /api/cities/resolve**

- **Purpose**: Convert city name to IATA airport code
- **Parameters**: `city` (city name)
- **Response**: JSON with airport information

```python
# Response Format
{
    "success": true,
    "iata": "BCN",
    "city": "Barcelona",
    "original_query": "barcelona"
}
```

#### 6.1.3 Testing Endpoints

**POST /test-flights**

- **Purpose**: Test flight search functionality
- **Parameters**: `origin`, `destination`, `date`
- **Response**: JSON with flight results

**POST /test-hotels**

- **Purpose**: Test hotel search functionality
- **Parameters**: `city`, `checkin`, `checkout`
- **Response**: JSON with hotel results

#### 6.1.4 Health Check Endpoint

**GET /health**

- **Purpose**: System health monitoring
- **Response**: JSON with system status

```python
# Response Format
{
    "status": "healthy",
    "version": "2.0.0",
    "debug": false,
    "api_status": "connected",
    "services": {
        "flight_service": "active",
        "accommodation_service": "active",
        "combination_engine": "active",
        "city_resolver": "active"
    }
}
```

---

## 7. User Interface Design

### 7.1 Frontend Architecture

#### 7.1.1 Technology Stack

- **HTML5**: Semantic markup with accessibility features
- **CSS3**: Modern styling with CSS Grid and Flexbox
- **Vanilla JavaScript**: Live autocomplete functionality
- **Progressive Enhancement**: Works without JavaScript

#### 7.1.2 Design System

- **Color Palette**:
  - Primary: #667eea (blue gradient)
  - Secondary: #764ba2 (purple gradient)
  - Success: #28a745
  - Warning: #ffc107
  - Error: #dc3545
- **Typography**: System fonts (-apple-system, BlinkMacSystemFont, 'Segoe UI')
- **Spacing**: 8px base unit (8px, 16px, 24px, 32px)
- **Border Radius**: 10px for cards, 5px for inputs

### 7.2 Page Specifications

#### 7.2.1 Home Page (`templates/index.html`)

```html
<!-- Key Components -->
<div class="hero">
    <h1>🌍 Holiday Engine</h1>
    <p>Find perfect flight + hotel combinations</p>
</div>

<div class="search-card">
    <form id="searchForm" action="/smart-search" method="post">
        <!-- City inputs with live autocomplete -->
        <div class="city-input">
            <input type="text" id="origin" name="origin" 
                   placeholder="From: City or Airport Code" 
                   autocomplete="off" required>
            <div class="city-suggestions" id="originSuggestions"></div>
        </div>
      
        <!-- Date inputs with validation -->
        <input type="date" id="departure" name="departure" required>
        <input type="date" id="return_date" name="return_date" required>
      
        <!-- Budget and travelers -->
        <input type="number" id="budget" name="budget" 
               placeholder="Budget (EUR, optional)">
        <select id="persons" name="persons">
            <option value="1">1 Person</option>
            <option value="2" selected>2 People</option>
        </select>
      
        <button type="submit">🔍 Search Travel Deals</button>
    </form>
</div>
```

#### 7.2.2 Results Page (`templates/results.html`)

```html
<!-- Tab Navigation -->
<div class="tab-nav">
    <button class="tab-button active" data-tab="combinations">
        🎯 Best Combinations ({{ combinations|length }})
    </button>
    <button class="tab-button" data-tab="flights">
        ✈️ All Flights ({{ outbound_flights|length + return_flights|length }})
    </button>
    <button class="tab-button" data-tab="accommodations">
        🏨 Accommodations ({{ hotels|length + airbnb_properties|length }})
    </button>
</div>

<!-- Tab Content with filtering and results display -->
<div class="tab-content">
    <!-- Results displayed in cards with pricing and ratings -->
</div>
```

### 7.3 JavaScript Functionality

#### 7.3.1 Live Autocomplete

```javascript
class CityAutocomplete {
    constructor(inputElement, suggestionsElement) {
        this.input = inputElement;
        this.suggestions = suggestionsElement;
        this.debounceTimer = null;
        this.cache = new Map();
        this.init();
    }
  
    async fetchSuggestions(query) {
        // Check cache first
        if (this.cache.has(query)) {
            this.displaySuggestions(this.cache.get(query));
            return;
        }
      
        try {
            const response = await fetch(`/api/cities/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();
          
            if (data.suggestions) {
                this.cache.set(query, data.suggestions);
                this.displaySuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
            this.hideSuggestions();
        }
    }
}
```

---

## 8. Development Guidelines

### 8.1 Code Standards

#### 8.1.1 Python Code Style

```python
# Style guide compliance
# - PEP 8 for Python code style
# - Type hints for function signatures where possible
# - Docstrings for public methods
# - Maximum line length: 100 characters

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ExampleService:
    """
    Example service demonstrating code standards
    """
  
    def __init__(self, api_client: ApiClient) -> None:
        """Initialize the service"""
        self.api_client = api_client
        self.cache: Dict[str, Any] = {}
  
    async def fetch_data(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from external API
      
        Args:
            endpoint: API endpoint to call
            params: Optional query parameters
          
        Returns:
            List of data items from API response
        """
        try:
            logger.info(f"Fetching data from {endpoint}")
            response = await self.api_client.get(endpoint, params=params)
            return response.data
          
        except Exception as e:
            logger.error(f"Failed to fetch data from {endpoint}: {e}")
            raise ApiClientError(f"Data fetch failed: {e}") from e
```

### 8.2 Testing Strategy

#### 8.2.1 Test Structure

The application includes a comprehensive test suite located in the `test/` directory:

- `test_integration.py`: API endpoint testing
- `test_scrapers.py`: External API integration testing
- `test_pytest_bench.py`: Performance benchmarking
- `test_nearest_simple.py`: City resolution testing
- `test_port_soller.py`: Specific location testing
- `run_tests.py`: Test runner script

#### 8.2.2 Running Tests

```bash
# Run all tests
python3 test/run_tests.py

# Run specific test categories
python3 test/test_integration.py
python3 test/test_scrapers.py
```

### 8.3 File Structure

```
holiday-engine/
├── main.py                    # FastAPI application
├── business_logic.py          # Core business logic
├── config/
│   ├── settings.py           # Configuration management
│   └── airports.csv          # Real airport database
├── services/
│   ├── city_resolver.py      # City-to-IATA resolution
│   ├── flight_service.py     # Flight search service
│   └── hotel_service.py      # Accommodation search service
├── utils/
│   ├── api_client.py         # Unified API client
│   └── data_parser.py        # Data parsers
├── templates/                # HTML templates
│   ├── index.html           # Main search interface
│   ├── results.html         # Three-tab results display
│   └── error.html           # Error handling
├── test/                     # Test suite
│   ├── run_tests.py         # Test runner
│   ├── test_integration.py  # Integration tests
│   └── test_scrapers.py     # Scraper tests
├── output/                  # CSV export directory
└── readme.md               # Project documentation
```

### 8.4 Development Commands

#### 8.4.1 Running the Application

```bash
# Run the development server
python3 main.py

# Access the application
# Main interface: http://localhost:8000
# Health check: http://localhost:8000/health
# Live autocomplete: http://localhost:8000/api/cities/autocomplete?q=Barcelona
```

#### 8.4.2 Environment Configuration

Create a `.env` file with:

```
APIFY_TOKEN=your_apify_token_here
DEBUG=True
LOG_LEVEL=INFO
EXPORT_CSV=True
```

---

## Conclusion

This Software Design Specification accurately reflects the current implementation of the Holiday Engine travel search platform. The document serves as both technical documentation and implementation guide for the existing codebase.

### Key Implementation Highlights:

1. **Service-Oriented Architecture**: Clean separation with services/, utils/, config/, and templates/ directories
2. **Live City Autocomplete**: Real-time suggestions using OpenStreetMap Nominatim API
3. **Intelligent Combination Engine**: Score-based ranking of travel packages
4. **Real Airport Database**: 7,000+ airports with distance-based matching
5. **Concurrent Processing**: Async/await for parallel API calls
6. **CSV Export**: Search result analysis and data export functionality
7. **Comprehensive Testing**: Multi-category test suite with integration tests

The platform is production-ready with robust error handling, mock data fallbacks, and a clean three-tab user interface for displaying search results.
