# services/hotel_service.py - Hotel & Accommodation Service
from typing import List, Dict, Any, Optional
import logging

from utils.api_client import ApifyClient
from utils.data_parser import HotelParser, AirbnbParser

logger = logging.getLogger(__name__)

class AccommodationService:
    """Service for hotel and Airbnb search operations"""
    
    def __init__(self, api_client: ApifyClient):
        self.api_client = api_client
        self.hotel_parser = HotelParser()
        self.airbnb_parser = AirbnbParser()
    
    async def search_hotels(
        self,
        city: str,
        checkin: str,
        checkout: str,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search hotels using Booking.com via Apify
        
        Args:
            city: City name (e.g., 'Barcelona')
            checkin: Check-in date in YYYY-MM-DD format
            checkout: Check-out date in YYYY-MM-DD format
            max_results: Maximum number of results to return
            
        Returns:
            List of hotel dictionaries
        """
        logger.info(f"Searching hotels in {city} ({checkin} - {checkout})")
        
        # Prepare actor input
        actor_input = {
            "currency": "EUR",
            "language": "en-us",
            "search": city,
            "sortBy": "review_score_and_price",
            "starsCountFilter": "any",
            "checkIn": checkin,
            "checkOut": checkout,
            "rooms": 1,
            "adults": 2,
            "children": 0,
            "includeAlternativeAccommodations": True,
            "destType": "city"
        }
        
        # Set options with maxItems
        options = {
            "maxItems": max(max_results * 4, 200),  # Request more to get better results
            "timeout": 120
        }
        
        try:
            # Call Apify API
            raw_data = await self.api_client.call_actor(
                "voyager~fast-booking-scraper",
                actor_input,
                options
            )
            
            if not raw_data:
                logger.warning(f"No hotel data received for {city}")
                return []
            
            # Parse hotels
            hotels = self.hotel_parser.parse_hotels(raw_data)
            
            # Limit results
            limited_hotels = hotels[:max_results]
            
            logger.info(f"Found {len(limited_hotels)} hotels for {city}")
            return limited_hotels
            
        except Exception as e:
            logger.error(f"Hotel search failed for {city}: {e}")
            raise
    
    async def search_airbnb(
        self,
        city: str,
        checkin: str,
        checkout: str,
        guests: int = 2,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search Airbnb properties
        
        Args:
            city: City name
            checkin: Check-in date in YYYY-MM-DD format  
            checkout: Check-out date in YYYY-MM-DD format
            guests: Number of guests
            max_results: Maximum number of results
            
        Returns:
            List of Airbnb property dictionaries
        """
        logger.info(f"Searching Airbnb in {city} for {guests} guests ({checkin} - {checkout})")
        
        # Prepare actor input
        actor_input = {
            "locationQueries": [city],
            "locale": "de-DE",
            "currency": "EUR",
            "checkIn": checkin,
            "checkOut": checkout,
            "adults": guests,
            "children": 0,
            "infants": 0,
            "pets": 0,
            "priceMin": 10,
            "priceMax": 999,
            "maxReviews": 0,
            "includeReviews": False
        }
        
        # Set options with maxItems
        options = {
            "maxItems": max_results,
            "timeout": 120
        }
        
        try:
            # Call Apify API
            raw_data = await self.api_client.call_actor(
                "tri_angle~new-fast-airbnb-scraper",
                actor_input,
                options
            )
            
            if not raw_data:
                logger.warning(f"No Airbnb data received for {city}")
                return []
            
            # Parse properties
            properties = self.airbnb_parser.parse_properties(raw_data)
            
            logger.info(f"Found {len(properties)} Airbnb properties for {city}")
            return properties
            
        except Exception as e:
            logger.error(f"Airbnb search failed for {city}: {e}")
            # Don't raise for Airbnb - it's optional
            return []
    
    async def search_all_accommodations(
        self,
        city: str,
        checkin: str, 
        checkout: str,
        guests: int = 2,
        max_hotels: int = 50,
        max_airbnb: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search both hotels and Airbnb properties concurrently
        
        Returns:
            Dict with 'hotels' and 'airbnb' lists
        """
        logger.info(f"Searching all accommodations in {city}")
        
        import asyncio
        
        # Search both concurrently
        hotel_task = self.search_hotels(city, checkin, checkout, max_hotels)
        airbnb_task = self.search_airbnb(city, checkin, checkout, guests, max_airbnb)
        
        try:
            hotels, airbnb_properties = await asyncio.gather(
                hotel_task,
                airbnb_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(hotels, Exception):
                logger.error(f"Hotel search failed: {hotels}")
                hotels = []
            
            if isinstance(airbnb_properties, Exception):
                logger.error(f"Airbnb search failed: {airbnb_properties}")
                airbnb_properties = []
            
            return {
                'hotels': hotels,
                'airbnb': airbnb_properties
            }
            
        except Exception as e:
            logger.error(f"Accommodation search failed: {e}")
            return {'hotels': [], 'airbnb': []}