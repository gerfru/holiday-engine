# Holiday-Engine: Flexible Flight Search and Data Export with Python and Kiwi.com API

## Project Description

This Python project enables you to **search for round-trip flights between any set of source and destination cities** for user-defined travel periods and settings. Flight data is retrieved from the [Kiwi.com Cheap Flights API](https://rapidapi.com/kiwicom/api/kiwi-com-cheap-flights/) via RapidAPI and automatically exported to Excel with all nested data flattened into columns for easy analysis.

## Features

- **Automated flight search** for flexible dates, routes, and passenger configurations
- **Multiple locations support**: Search from multiple origin cities/airports to destinations
- **Comprehensive query parameters**: Filter by days, stops, baggage, price, cabin class, and more
- **Dynamic Excel export**: All nested API data fields are automatically flattened into spreadsheet columns
- **Built-in data processing**: Integrated JSON flattening and DataFrame creation
- **Environment-based configuration**: Secure API key management using .env files

## Requirements

- Python 3.8+
- Required Python packages:
  - [requests](https://pypi.org/project/requests/) - HTTP library for API calls
  - [pandas](https://pypi.org/project/pandas/) - Data manipulation and analysis
  - [openpyxl](https://pypi.org/project/openpyxl/) - Excel file operations
  - [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment variable management
- RapidAPI account with access to the Kiwi.com Cheap Flights API

## Setup

### 1. Installation

Clone this repository or copy the scripts to your project directory:

```bash
git clone <repository-url>
cd holiday-engine
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install requests pandas openpyxl python-dotenv
```

### 3. API Configuration

1. Sign up at [RapidAPI](https://rapidapi.com/) and subscribe to the [Kiwi.com Cheap Flights API](https://rapidapi.com/kiwicom/api/kiwi-com-cheap-flights/)
2. Create a `.env` file in your project directory with your RapidAPI credentials:

```env
X_RAPIDAPI_KEY=your_rapidapi_key_here
X_RAPIDAPI_HOST=kiwi-com-cheap-flights.p.rapidapi.com
```

### 4. Project Structure

```
holiday-engine/
├── flights-api.py          # Main flight search script with integrated Excel export
├── .env                    # API credentials (create this)
├── output/                 # Generated output files
│   └── flights_dynamic.xlsx # Processed Excel file with flattened data
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Usage

### Running the Flight Search

1. **Configure your search parameters** by editing the `querystring` dictionary in `flights-api.py`
2. **Run the script**:

```bash
python flights-api.py
```

The script will:
- Fetch flight data from the Kiwi.com API
- Automatically flatten all nested JSON data
- Export results to `output/flights_dynamic.xlsx`

### Current Example Configuration

The script is currently configured to search for flights from Austria (Graz/Vienna) to Rhodes, Greece:

```python
querystring = {
    "source": "Country:AT, City:Graz_AT, City:Vienna_AT",
    "destination": "City:rhodes_gr",
    "currency": "eur",
    "locale": "en",
    "adults": "1",
    "children": "0",
    "infants": "0",
    "handbags": "1",
    "holdbags": "0",
    "cabinClass": "ECONOMY",
    "sortBy": "QUALITY",
    "sortOrder": "ASCENDING",
    "inboundDepartureDateStart": "2025-06-23T00:00:00",
    "inboundDepartureDateEnd": "2025-06-30T23:59:59",
    "limit": "20"
}
```

## Customization

### Key Search Parameters

The script supports extensive customization through the `querystring` parameters:

#### Location Parameters
- **source**: Origin cities/airports (e.g., `"Country:AT, City:Graz_AT, City:Vienna_AT"`)
- **destination**: Destination cities/airports (e.g., `"City:rhodes_gr"`)

#### Date Parameters  
- **inboundDepartureDateStart**: Return flight start date (ISO format)
- **inboundDepartureDateEnd**: Return flight end date (ISO format)
- **outbound**: Preferred departure days of week

#### Passenger Configuration
- **adults**: Number of adult passengers
- **children**: Number of children
- **infants**: Number of infants

#### Flight Preferences
- **cabinClass**: `ECONOMY`, `PREMIUM_ECONOMY`, `BUSINESS`, `FIRST`
- **handbags**: Number of carry-on bags allowed
- **holdbags**: Number of checked bags
- **sortBy**: `QUALITY`, `PRICE`, `DURATION`
- **sortOrder**: `ASCENDING`, `DESCENDING`

#### Advanced Options
- **allowReturnFromDifferentCity**: Allow return from different city
- **allowChangeInboundDestination**: Flexible return destination
- **enableSelfTransfer**: Enable self-transfer connections
- **allowOvernightStopover**: Allow overnight layovers
- **limit**: Maximum number of results (default: 20)

### Data Processing Features

The script includes a built-in `flatten_dict()` function that:
- **Flattens nested JSON**: Converts complex nested structures to flat columns
- **Handles arrays**: Processes lists of flight segments, baggage info, etc.
- **Preserves all data**: Every field from the API response is included
- **Uses dot notation**: Creates readable column names like `segments.0.departure.time`

## Output

### Excel Output (`output/flights_dynamic.xlsx`)
- **Comprehensive flight data**: All flight information in tabular format
- **Flattened structure**: Nested JSON data converted to individual columns
- **Ready for analysis**: Suitable for sorting, filtering, and pivot tables
- **All flight details**: Prices, times, airlines, airports, baggage allowances
- **Booking information**: Direct links and booking details included

The Excel file contains columns such as:
- `price.amount`, `price.currency` - Flight pricing
- `segments.0.departure.time`, `segments.0.arrival.time` - Flight times
- `segments.0.airline.name`, `segments.0.airline.code` - Airline details
- `segments.0.departure.airport.name` - Airport information
- `baggageOptions.0.price`, `baggageOptions.0.category` - Baggage details
- And many more automatically generated columns based on API response structure

## Code Structure

### Main Components

The `flights-api.py` script contains several key components:

#### 1. Environment Setup
```python
from dotenv import load_dotenv
import os

load_dotenv()
RAPIDAPI_KEY = os.getenv('X_RAPIDAPI_KEY')
RAPIDAPI_HOST = os.getenv('X_RAPIDAPI_HOST')
```

#### 2. API Configuration
```python
url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"
headers = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}
```

#### 3. Data Flattening Function
The `flatten_dict()` function recursively processes nested JSON data:
- Handles dictionaries by creating dot-separated keys
- Processes arrays by creating indexed keys (e.g., `segments.0`, `segments.1`)
- Converts all complex structures to flat key-value pairs

#### 4. DataFrame Creation and Export
```python
rows = [flatten_dict(x) for x in data.get('itineraries', [])]
df = pd.DataFrame(rows)
df.to_excel('output/flights_dynamic.xlsx', index=False)
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: 
   - Verify your RapidAPI credentials in the `.env` file
   - Ensure both `X_RAPIDAPI_KEY` and `X_RAPIDAPI_HOST` are set correctly

2. **Rate Limiting**: 
   - The API has usage limits - check your RapidAPI dashboard
   - Consider reducing the `limit` parameter in your search

3. **Invalid Location Codes**: 
   - Verify city/airport codes are correct (e.g., `City:rhodes_gr`)
   - Use the format `Country:CODE` or `City:NAME_COUNTRY` for locations

4. **Date Format Issues**: 
   - Ensure dates are in ISO format: `YYYY-MM-DDTHH:MM:SS`
   - Check that return dates are after departure dates

5. **Empty Results**: 
   - Try broadening your search criteria (dates, destinations)
   - Check if the route is actually available
   - Verify seasonal availability for your destination

6. **Output Directory**: 
   - Ensure the `output/` directory exists
   - Check file permissions for writing Excel files

### Debug Tips

- **Enable JSON saving**: Uncomment the JSON saving code to inspect raw API responses
- **Check API response**: Print `response.status_code` and `response.text` for debugging
- **Validate parameters**: Review the Kiwi.com API documentation for valid parameter values

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and personal use. Please respect the Kiwi.com API terms of service and rate limits. The authors are not responsible for any misuse of this tool or violations of API terms.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review the Kiwi.com API documentation
- Open an issue in this repository

---

**Happy travels! ✈️**