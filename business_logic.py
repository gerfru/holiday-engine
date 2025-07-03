# business_logic.py - Core Business Logic
from typing import List, Dict, Any, Optional
import logging
import os
import csv
from datetime import datetime

logger = logging.getLogger(__name__)

class TravelCombinationEngine:
    """Engine for creating intelligent travel combinations"""
    
    def create_combinations(
        self,
        flights: List[Dict[str, Any]],
        hotels: List[Dict[str, Any]],
        budget: Optional[int] = None,
        search_params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Create optimized flight + accommodation combinations
        
        Args:
            flights: List of flight options (can be round-trip or one-way)
            hotels: List of hotel options
            budget: Optional budget constraint in EUR
            search_params: Optional search parameters including nights, persons, etc.
            
        Returns:
            List of optimized combinations sorted by score
        """
        logger.info("Creating travel combinations...")
        
        # Default parameters
        if search_params is None:
            search_params = {}
        
        nights = search_params.get('nights', 7)
        persons = search_params.get('persons', 2)
        
        # Prepare accommodation options (hotels only for now)
        all_accommodations = self._prepare_accommodations(hotels, [])
        
        if not flights:
            logger.warning("No flights available for combinations")
            return []
        
        if not all_accommodations:
            logger.warning("No accommodations available for combinations") 
            return []
        
        # Generate combinations
        combinations = []
        
        # Limit options for performance (top 3 of each)
        for flight in flights[:3]:
            for accommodation in all_accommodations:
                
                combination = self._create_single_combination_simple(
                    flight, accommodation, nights, persons, budget
                )
                
                if combination:  # Only add valid combinations
                    combinations.append(combination)
        
        # Sort by score and return top combinations
        combinations.sort(key=lambda x: x['score'], reverse=True)
        top_combinations = combinations[:5]
        
        logger.info(f"Created {len(top_combinations)} optimized combinations")
        return top_combinations
    
    def _prepare_accommodations(
        self, 
        hotels: List[Dict[str, Any]], 
        airbnb_properties: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prepare and mark accommodation types"""
        accommodations = []
        
        # Add top hotels
        for hotel in hotels[:3]:
            hotel_copy = hotel.copy()
            hotel_copy['accommodation_type'] = 'hotel'
            accommodations.append(hotel_copy)
        
        # Add top Airbnb properties
        for airbnb in airbnb_properties[:3]:
            airbnb_copy = airbnb.copy()
            airbnb_copy['accommodation_type'] = 'airbnb'
            accommodations.append(airbnb_copy)
        
        return accommodations
    
    def _create_single_combination_simple(
        self,
        flight: Dict[str, Any],
        accommodation: Dict[str, Any],
        nights: int,
        persons: int,
        budget: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Create a single travel combination with simplified flight handling"""
        
        try:
            # Calculate flight costs (multiply by persons)
            flight_cost = flight.get('price_eur', flight.get('price', 0)) * persons
            
            # Calculate accommodation cost
            accommodation_cost = accommodation.get('price_per_night', accommodation.get('price', 0)) * nights
            
            # Calculate total cost
            total_cost = flight_cost + accommodation_cost
            
            # Budget filter (allow 20% over budget for flexibility)
            if budget and total_cost > budget * 1.2:
                return None
            
            # Calculate score
            score = self._calculate_combination_score(
                total_cost, accommodation.get('rating', 3.0), budget
            )
            
            combination = {
                'flight': flight,
                'hotel': accommodation,
                'accommodation_type': accommodation.get('accommodation_type', 'hotel'),
                'flight_cost': flight_cost,
                'accommodation_cost': accommodation_cost,
                'total_price': total_cost,
                'nights': nights,
                'persons': persons,
                'score': score,
                'cost_per_person': total_cost / persons,
                'cost_per_night': total_cost / nights if nights > 0 else total_cost,
                'recommendation_reason': f"Good value at €{total_cost} for {persons} person(s)"
            }
            
            logger.debug(f"Created combination: €{total_cost} total (score: {score})")
            return combination
            
        except Exception as e:
            logger.warning(f"Error creating combination: {e}")
            return None
    
    def _create_single_combination(
        self,
        outbound_flight: Dict[str, Any],
        return_flight: Dict[str, Any],
        accommodation: Dict[str, Any],
        nights: int,
        persons: int,
        budget: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Create a single travel combination with cost calculation"""
        
        try:
            # Calculate flight costs (multiply by persons)
            flight_cost = (outbound_flight['price'] + return_flight['price']) * persons
            
            # Calculate accommodation cost
            accommodation_cost = accommodation['price'] * nights
            
            # Calculate total cost
            total_cost = flight_cost + accommodation_cost
            
            # Budget filter (allow 20% over budget for flexibility)
            if budget and total_cost > budget * 1.2:
                return None
            
            # Calculate score
            score = self._calculate_combination_score(
                total_cost, accommodation['rating'], budget
            )
            
            combination = {
                'outbound_flight': outbound_flight,
                'return_flight': return_flight,
                'accommodation': accommodation,
                'accommodation_type': accommodation['accommodation_type'],
                'flight_cost': flight_cost,
                'accommodation_cost': accommodation_cost,
                'total_cost': total_cost,
                'nights': nights,
                'persons': persons,
                'score': score,
                'cost_per_person': total_cost / persons,
                'cost_per_night': total_cost / nights if nights > 0 else total_cost
            }
            
            logger.debug(f"Created combination: €{total_cost} total (score: {score})")
            return combination
            
        except Exception as e:
            logger.warning(f"Error creating combination: {e}")
            return None
    
    def _calculate_combination_score(
        self, 
        total_cost: float, 
        accommodation_rating: float, 
        budget: Optional[int]
    ) -> float:
        """
        Calculate combination score based on cost and quality
        
        Higher score = better combination
        """
        score = 0.0
        
        # Accommodation rating component (0-50 points)
        score += accommodation_rating * 10
        
        # Budget/cost component (0-50 points)
        if budget:
            if total_cost <= budget * 0.8:  # Under 80% of budget
                score += 50
            elif total_cost <= budget:  # Within budget
                score += 30
            elif total_cost <= budget * 1.1:  # Up to 10% over budget
                score += 15
            else:  # More than 10% over budget
                score += 0
        else:
            # No budget specified - prefer lower prices
            # Normalize cost to 0-50 scale (assuming max reasonable cost ~2000)
            normalized_cost = min(total_cost / 2000, 1.0)
            score += 50 * (1 - normalized_cost)  # Lower cost = higher score
        
        return round(score, 1)

# Export functionality
async def export_search_results(
    search_results: Dict[str, Any], 
    search_params: Dict[str, Any]
) -> None:
    """Export search results to CSV files for analysis"""
    
    try:
        from config.settings import settings
        
        # Generate timestamp and search ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_id = f"{search_params['origin']}_{search_params['destination']}_{timestamp}"
        
        logger.info(f"Exporting search results: {search_id}")
        
        # Export flights
        await _export_flights(search_results['flights'], search_params, search_id)
        
        # Export accommodations
        await _export_accommodations(search_results['accommodations'], search_params, search_id)
        
        logger.info(f"Search results exported successfully: {search_id}")
        
    except Exception as e:
        logger.error(f"Failed to export search results: {e}")

async def _export_flights(
    flights: Dict[str, List[Dict[str, Any]]], 
    search_params: Dict[str, Any], 
    search_id: str
) -> None:
    """Export flight data to CSV"""
    
    from config.settings import settings
    
    if not flights['outbound'] and not flights['return']:
        return
    
    flights_file = os.path.join(settings.output_directory, f"flights_{search_id}.csv")
    
    with open(flights_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'search_timestamp', 'search_origin', 'search_destination', 
            'search_departure', 'search_return', 'search_persons', 'search_budget',
            'flight_type', 'airline', 'departure_time', 'duration', 'stops', 
            'price_eur', 'source', 'booking_url', 'date'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write outbound flights
        for flight in flights['outbound']:
            writer.writerow({
                'search_timestamp': search_id.split('_')[-1],
                'search_origin': search_params['origin'],
                'search_destination': search_params['destination'],
                'search_departure': search_params['departure'],
                'search_return': search_params['return_date'],
                'search_persons': search_params['persons'],
                'search_budget': search_params.get('budget', ''),
                'flight_type': 'outbound',
                'airline': flight.get('airline', ''),
                'departure_time': flight.get('time', ''),
                'duration': flight.get('duration', ''),
                'stops': flight.get('stops', ''),
                'price_eur': flight.get('price', ''),
                'source': flight.get('source', ''),
                'booking_url': flight.get('url', ''),
                'date': flight.get('date', '')
            })
        
        # Write return flights
        for flight in flights['return']:
            writer.writerow({
                'search_timestamp': search_id.split('_')[-1],
                'search_origin': search_params['origin'],
                'search_destination': search_params['destination'],
                'search_departure': search_params['departure'],
                'search_return': search_params['return_date'],
                'search_persons': search_params['persons'],
                'search_budget': search_params.get('budget', ''),
                'flight_type': 'return',
                'airline': flight.get('airline', ''),
                'departure_time': flight.get('time', ''),
                'duration': flight.get('duration', ''),
                'stops': flight.get('stops', ''),
                'price_eur': flight.get('price', ''),
                'source': flight.get('source', ''),
                'booking_url': flight.get('url', ''),
                'date': flight.get('date', '')
            })
    
    logger.info(f"Exported flights to {flights_file}")

async def _export_accommodations(
    accommodations: Dict[str, List[Dict[str, Any]]], 
    search_params: Dict[str, Any], 
    search_id: str
) -> None:
    """Export accommodation data to CSV"""
    
    from config.settings import settings
    
    # Export hotels
    if accommodations['hotels']:
        await _export_hotels(accommodations['hotels'], search_params, search_id)
    
    # Export Airbnb
    if accommodations['airbnb']:
        await _export_airbnb(accommodations['airbnb'], search_params, search_id)

async def _export_hotels(
    hotels: List[Dict[str, Any]], 
    search_params: Dict[str, Any], 
    search_id: str
) -> None:
    """Export hotel data to CSV"""
    
    from config.settings import settings
    
    hotels_file = os.path.join(settings.output_directory, f"hotels_{search_id}.csv")
    
    with open(hotels_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'search_timestamp', 'search_origin', 'search_destination', 
            'search_departure', 'search_return', 'search_persons', 'search_budget', 'nights',
            'hotel_name', 'rating', 'location', 'type', 'price_total_eur', 
            'price_per_night_eur', 'source', 'booking_url', 'checkin', 'checkout'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        nights = search_params['nights']
        
        for hotel in hotels:
            writer.writerow({
                'search_timestamp': search_id.split('_')[-1],
                'search_origin': search_params['origin'],
                'search_destination': search_params['destination'],
                'search_departure': search_params['departure'],
                'search_return': search_params['return_date'],
                'search_persons': search_params['persons'],
                'search_budget': search_params.get('budget', ''),
                'nights': nights,
                'hotel_name': hotel.get('name', ''),
                'rating': hotel.get('rating', ''),
                'location': hotel.get('location', ''),
                'type': hotel.get('type', ''),
                'price_total_eur': hotel.get('price', 0) * nights,
                'price_per_night_eur': hotel.get('price', ''),
                'source': hotel.get('source', ''),
                'booking_url': hotel.get('url', ''),
                'checkin': search_params['departure'],
                'checkout': search_params['return_date']
            })
    
    logger.info(f"Exported hotels to {hotels_file}")

async def _export_airbnb(
    airbnb_properties: List[Dict[str, Any]], 
    search_params: Dict[str, Any], 
    search_id: str
) -> None:
    """Export Airbnb data to CSV"""
    
    from config.settings import settings
    
    airbnb_file = os.path.join(settings.output_directory, f"airbnb_{search_id}.csv")
    
    with open(airbnb_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'search_timestamp', 'search_origin', 'search_destination',
            'search_departure', 'search_return', 'search_persons', 'search_budget', 'nights',
            'property_name', 'rating', 'review_count', 'property_type', 
            'person_capacity', 'location', 'price_total_eur', 'price_per_night_eur',
            'badges', 'source', 'booking_url', 'checkin', 'checkout'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        nights = search_params['nights']
        
        for property_item in airbnb_properties:
            # Handle badges list
            badges_str = ', '.join(property_item.get('badges', [])[:5])
            
            writer.writerow({
                'search_timestamp': search_id.split('_')[-1],
                'search_origin': search_params['origin'],
                'search_destination': search_params['destination'],
                'search_departure': search_params['departure'],
                'search_return': search_params['return_date'],
                'search_persons': search_params['persons'],
                'search_budget': search_params.get('budget', ''),
                'nights': nights,
                'property_name': property_item.get('name', ''),
                'rating': property_item.get('rating', ''),
                'review_count': property_item.get('review_count', ''),
                'property_type': property_item.get('property_type', ''),
                'person_capacity': property_item.get('person_capacity', ''),
                'location': property_item.get('location', ''),
                'price_total_eur': property_item.get('price', 0) * nights,
                'price_per_night_eur': property_item.get('price', ''),
                'badges': badges_str,
                'source': property_item.get('source', ''),
                'booking_url': property_item.get('url', ''),
                'checkin': search_params['departure'],
                'checkout': search_params['return_date']
            })
    
    logger.info(f"Exported Airbnb properties to {airbnb_file}")

# Utility functions for combination analysis
def analyze_combination_statistics(combinations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze combination statistics for insights"""
    
    if not combinations:
        return {"error": "No combinations to analyze"}
    
    # Calculate statistics
    total_costs = [c['total_cost'] for c in combinations]
    flight_costs = [c['flight_cost'] for c in combinations]
    accommodation_costs = [c['accommodation_cost'] for c in combinations]
    scores = [c['score'] for c in combinations]
    
    # Count accommodation types
    hotel_count = sum(1 for c in combinations if c['accommodation_type'] == 'hotel')
    airbnb_count = sum(1 for c in combinations if c['accommodation_type'] == 'airbnb')
    
    return {
        "total_combinations": len(combinations),
        "cost_statistics": {
            "min_total": min(total_costs),
            "max_total": max(total_costs),
            "avg_total": sum(total_costs) / len(total_costs),
            "avg_flight_cost": sum(flight_costs) / len(flight_costs),
            "avg_accommodation_cost": sum(accommodation_costs) / len(accommodation_costs)
        },
        "quality_statistics": {
            "min_score": min(scores),
            "max_score": max(scores),
            "avg_score": sum(scores) / len(scores)
        },
        "accommodation_breakdown": {
            "hotels": hotel_count,
            "airbnb": airbnb_count
        },
        "best_combination": combinations[0] if combinations else None
    }