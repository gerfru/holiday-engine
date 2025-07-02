# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Holiday Engine is a Python-based travel comparison web application built with FastAPI. It searches for flights and hotels using Apify APIs and presents intelligent flight+hotel combinations to users.

## Architecture

### Core Components

- **main.py**: FastAPI application with HTML template rendering
  - `/smart-search` endpoint: Main search functionality combining flights and hotels
  - `/test-flights` endpoint: Simple flight testing endpoint
  - Template rendering using Jinja2 for HTML responses

- **travel_api.py**: External API integration layer
  - `search_flights_apify()`: Uses jupri/skyscanner-flight Apify actor
  - `search_hotels_apify()`: Uses voyager/booking-scraper Apify actor
  - Includes mock data fallbacks when API tokens are unavailable
  - Robust error handling and data parsing

- **smart_city_lookup.py**: City-to-IATA code resolution system
  - Hybrid lookup: hardcoded popular destinations + API fallback + fuzzy matching
  - Supports German and English city names with umlauts
  - Includes Graz (GRZ) and other Austrian airports

- **templates/**: Jinja2 HTML templates
  - `index.html`: Main search form with intelligent city autocomplete
  - `results.html`: Display search results
  - `error.html`: Error page

## Development Commands

### Running the Application
```bash
# Run the development server
python3 main.py

# Access the application
# Main interface: http://localhost:8000
# Health check: http://localhost:8000/health
# Test endpoint: http://localhost:8000/test-flights
```

### Testing Individual Components
```bash
# Test travel API functions
python3 travel_api.py

# Test city lookup system
python3 smart_city_lookup.py
```

### Dependencies
The application uses Python 3.12+ with these key dependencies:
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `httpx`: HTTP client for API calls
- `jinja2`: Template engine
- `python-dotenv`: Environment variable management

## Environment Configuration

Create a `.env` file with:
```
APIFY_TOKEN=your_apify_token_here
```

If no token is provided, the application falls back to mock data for development.

## Key Implementation Details

### Smart Search Logic
1. Search outbound and return flights via Apify
2. Search hotels in destination city
3. Create flight+hotel combinations within budget
4. Score combinations by price-to-rating ratio
5. Return top 5 results

### City Input Handling
- Client-side autocomplete with CITY_MAP in templates/index.html:364
- Server-side validation through smart_city_lookup.py
- Supports both city names and IATA codes
- Fuzzy matching for typos

### API Integration
- Uses Apify actors for real data: jupri/skyscanner-flight and voyager/booking-scraper
- Graceful fallback to mock data if APIs fail
- Proper error handling and response parsing

## File Structure
```
holiday-engine/
├── main.py              # FastAPI application
├── travel_api.py        # API integration layer
├── smart_city_lookup.py # City-to-IATA resolution
├── templates/           # HTML templates
│   ├── index.html       # Main search interface
│   ├── results.html     # Search results display
│   └── error.html       # Error handling
├── output/              # (empty directory)
├── json.json            # (large data file - 1.7MB)
└── .gitignore          # Git ignore rules
```

## Testing Strategy

The application includes comprehensive fallback mechanisms:
- Mock data when API tokens unavailable
- Graceful error handling for external API failures
- Client-side and server-side input validation
- Health check endpoint for monitoring