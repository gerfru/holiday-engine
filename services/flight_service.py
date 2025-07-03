# services/flight_service.py - Clean Flight Service
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime
import logging

from utils.api_client import ApifyClient
from utils.data_parser import FlightParser

logger = logging.getLogger(__name__)

class FlightService:
    """Service for flight search operations"""
    
    def __init__(self, api_client: ApifyClient):
        self.api_client = api_client
        self.parser = FlightParser()
    
    async def search_flights(
        self, 
        origin: str, 
        destination: str, 
        date: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search flights using Skyscanner via Apify
        
        Args:
            origin: IATA airport code (e.g., 'VIE')
            destination: IATA airport code (e.g., 'FCO') 
            date: Departure date in YYYY-MM-DD format
            max_results: Maximum number of results to return
            
        Returns:
            List of flight dictionaries with airline, price, time, duration
        """
        logger.info(f"Searching flights: {origin} → {destination} on {date}")
        
        # Prepare actor input
        actor_input = {
            "origin.0": origin.upper(),
            "target.0": destination.upper(),
            "depart.0": date,
            "market": "DE",
            "currency": "EUR"
        }
        
        try:
            # Call Apify API with retry logic
            raw_data = await self.api_client.call_actor(
                "jupri~skyscanner-flight",
                actor_input
            )
            
            if not raw_data:
                logger.warning(f"No data received for {origin} → {destination}")
                return []
            
            # Parse flights
            flights = self.parser.parse_flights(raw_data)
            
            # Sort by price and limit results
            flights.sort(key=lambda x: x.get('price', 999999))
            limited_flights = flights[:max_results]
            
            logger.info(f"Found {len(limited_flights)} flights for {origin} → {destination}")
            return limited_flights
            
        except Exception as e:
            logger.error(f"Flight search failed for {origin} → {destination}: {e}")
            raise
    
    async def search_round_trip(
        self,
        origin: str,
        destination: str, 
        departure_date: str,
        return_date: str,
        max_results_per_direction: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search round-trip flights
        
        Returns:
            Dict with 'outbound' and 'return' flight lists
        """
        logger.info(f"Searching round-trip: {origin} ↔ {destination}")
        
        # Search both directions concurrently
        outbound_task = self.search_flights(origin, destination, departure_date, max_results_per_direction)
        return_task = self.search_flights(destination, origin, return_date, max_results_per_direction)
        
        try:
            outbound_flights, return_flights = await asyncio.gather(
                outbound_task, 
                return_task,
                return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(outbound_flights, Exception):
                logger.error(f"Outbound flight search failed: {outbound_flights}")
                outbound_flights = []
            
            if isinstance(return_flights, Exception):
                logger.error(f"Return flight search failed: {return_flights}")
                return_flights = []
            
            return {
                'outbound': outbound_flights,
                'return': return_flights
            }
            
        except Exception as e:
            logger.error(f"Round-trip search failed: {e}")
            return {'outbound': [], 'return': []}
    
    def calculate_flight_combinations(
        self,
        outbound_flights: List[Dict[str, Any]],
        return_flights: List[Dict[str, Any]], 
        persons: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Calculate flight cost combinations for given number of persons
        
        Args:
            outbound_flights: List of outbound flight options
            return_flights: List of return flight options
            persons: Number of travelers
            
        Returns:
            List of flight combinations with total costs
        """
        combinations = []
        
        for outbound in outbound_flights[:3]:  # Limit to top 3
            for return_flight in return_flights[:3]:
                total_cost = (outbound['price'] + return_flight['price']) * persons
                
                combination = {
                    'outbound_flight': outbound,
                    'return_flight': return_flight,
                    'total_cost': total_cost,
                    'persons': persons,
                    'cost_per_person': outbound['price'] + return_flight['price']
                }
                
                combinations.append(combination)
        
        # Sort by total cost
        combinations.sort(key=lambda x: x['total_cost'])
        
        logger.info(f"Generated {len(combinations)} flight combinations for {persons} persons")
        return combinations