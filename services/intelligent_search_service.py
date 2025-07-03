# services/intelligent_search_service.py
"""
Intelligenter Search Service der in die bestehende Holiday Engine Architektur integriert wird
Nutzt LLM über MCP für natürlichsprachliche Verarbeitung
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .city_resolver import CityResolver
from .flight_service import FlightService  
from .hotel_service import HotelService
from ..business_logic import TravelCombinationEngine
from ..config.settings import Settings
from ..utils.api_client import APIClient


class IntelligentSearchService:
    """Service für intelligente, LLM-gestützte Reisesuche"""
    
    def __init__(self):
        self.city_resolver = CityResolver()
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        self.combination_engine = TravelCombinationEngine()
        self.api_client = APIClient()
        self.settings = Settings()
    
    async def process_natural_query(self, query: str, origin: str = "Wien") -> Dict[str, Any]:
        """
        Verarbeitet natürlichsprachliche Anfrage und führt intelligente Suche durch
        
        Args:
            query: Natürlichsprachliche Anfrage wie "Finde mir etwas Romantisches in Italien unter 1000€"
            origin: Abflugort (Standard: Wien)
            
        Returns:
            Strukturierte Suchergebnisse mit Empfehlungen
        """
        
        # 1. LLM-Analyse der Anfrage
        parsed_query = await self._analyze_query_with_llm(query)
        
        # 2. Destination Resolution mit deinem bestehenden Service
        destination_info = await self._resolve_destination(parsed_query["destination"])
        
        # 3. Intelligente Datumsauswahl
        optimized_dates = await self._optimize_travel_dates(
            destination_info, parsed_query
        )
        
        # 4. Multi-Parameter Suche
        search_results = await self._perform_multi_search(
            origin, destination_info, optimized_dates, parsed_query
        )
        
        # 5. LLM-gestützte Empfehlungen
        recommendations = await self._generate_smart_recommendations(
            search_results, parsed_query
        )
        
        return {
            "query_analysis": parsed_query,
            "destination": destination_info,
            "optimized_dates": optimized_dates,
            "search_results": search_results,
            "recommendations": recommendations
        }
    
    async def _analyze_query_with_llm(self, query: str) -> Dict[str, Any]:
        """Nutzt LLM über MCP um natürlichsprachliche Anfrage zu strukturieren"""
        
        prompt = f"""
        Analysiere diese Reiseanfrage und extrahiere strukturierte Informationen:
        
        Anfrage: "{query}"
        
        Bitte antworte nur mit einem JSON-Objekt im folgenden Format:
        {{
            "destination": "extrahiertes Reiseziel",
            "budget_max": "Budget in EUR oder null",
            "duration_days": "Anzahl Tage oder Bereich [min, max]",
            "travel_type": "romantic/family/business/adventure/leisure/cultural",
            "month": "gewünschter Monat oder null",
            "preferences": {{
                "accommodation_type": "hotel/airbnb/luxury/budget",
                "activities": ["liste", "von", "aktivitäten"],
                "priority": "price/comfort/location/experience"
            }},
            "flexibility": {{
                "dates": "flexible/fixed",
                "destination": "flexible/fixed", 
                "budget": "flexible/fixed"
            }}
        }}
        
        Wichtig: Antworte NUR mit dem JSON-Objekt, keine anderen Texte.
        """
        
        try:
            # Hier würdest du window.claude.complete verwenden, wenn im MCP Server
            # Für jetzt simulieren wir intelligente Extraktion
            llm_response = await self._call_llm_via_mcp(prompt)
            return json.loads(llm_response)
        
        except Exception as e:
            # Fallback: Einfache Regel-basierte Extraktion
            return self._fallback_query_parsing(query)
    
    async def _call_llm_via_mcp(self, prompt: str) -> str:
        """Ruft LLM über MCP Client auf"""
        
        # Hier würde die echte MCP-Integration stehen
        # Für Demo: Simulierte intelligente Antwort
        if "romantisch" in prompt.lower() or "romantic" in prompt.lower():
            return json.dumps({
                "destination": "Italien",
                "budget_max": 1000,
                "duration_days": [7, 10],
                "travel_type": "romantic",
                "month": "12",
                "preferences": {
                    "accommodation_type": "hotel",
                    "activities": ["sightseeing", "fine_dining", "cultural_tours"],
                    "priority": "comfort"
                },
                "flexibility": {
                    "dates": "flexible",
                    "destination": "fixed",
                    "budget": "flexible"
                }
            })
        
        # Default-Response
        return json.dumps({
            "destination": "Italien",
            "budget_max": None,
            "duration_days": [7, 7],
            "travel_type": "leisure",
            "month": None,
            "preferences": {
                "accommodation_type": "hotel",
                "activities": ["sightseeing"],
                "priority": "price"
            },
            "flexibility": {
                "dates": "flexible",
                "destination": "fixed",
                "budget": "flexible"
            }
        })
    
    def _fallback_query_parsing(self, query: str) -> Dict[str, Any]:
        """Fallback: Regel-basierte Parsing wenn LLM nicht verfügbar"""
        
        query_lower = query.lower()
        
        # Einfache Keyword-Extraktion
        destination = "Italien"  # Default
        if "spanien" in query_lower:
            destination = "Spanien"
        elif "griechenland" in query_lower:
            destination = "Griechenland"
        
        # Budget-Extraktion
        budget = None
        import re
        budget_match = re.search(r'(\d+)€', query)
        if budget_match:
            budget = int(budget_match.group(1))
        
        # Travel Type
        travel_type = "leisure"
        if any(word in query_lower for word in ["romantisch", "romantic", "paar"]):
            travel_type = "romantic"
        
        return {
            "destination": destination,
            "budget_max": budget,
            "duration_days": [7, 10],
            "travel_type": travel_type,
            "month": None,
            "preferences": {
                "accommodation_type": "hotel",
                "activities": ["sightseeing"],
                "priority": "price"
            },
            "flexibility": {
                "dates": "flexible",
                "destination": "fixed", 
                "budget": "flexible"
            }
        }
    
    async def _resolve_destination(self, destination: str) -> Dict[str, Any]:
        """Nutzt deinen bestehenden CityResolver"""
        
        try:
            # Dein bestehender Service
            resolved = await self.city_resolver.resolve_city(destination)
            return resolved
        except Exception as e:
            # Fallback
            return {
                "city": destination,
                "country": "Unknown",
                "airport_code": destination[:3].upper(),
                "coordinates": None
            }
    
    async def _optimize_travel_dates(self, destination_info: Dict, parsed_query: Dict) -> List[Dict]:
        """Optimiert Reisedaten basierend auf Destination und Präferenzen"""
        
        # Generiere Datumskandidaten
        base_dates = self._generate_date_candidates(parsed_query)
        
        # Für jedes Datum: Bewertung basierend auf verschiedenen Faktoren
        optimized_dates = []
        
        for date_range in base_dates:
            score = await self._calculate_date_score(
                destination_info, date_range, parsed_query
            )
            
            optimized_dates.append({
                "check_in": date_range["check_in"],
                "check_out": date_range["check_out"],
                "duration_days": date_range["duration_days"],
                "optimization_score": score,
                "score_breakdown": score["breakdown"]
            })
        
        # Sortiere nach Score
        optimized_dates.sort(key=lambda x: x["optimization_score"]["total"], reverse=True)
        
        return optimized_dates[:5]  # Top 5 Daten
    
    def _generate_date_candidates(self, parsed_query: Dict) -> List[Dict]:
        """Generiert Datumskandidaten basierend auf Anfrage"""
        
        candidates = []
        duration_range = parsed_query["duration_days"]
        
        if isinstance(duration_range, list):
            min_days, max_days = duration_range
        else:
            min_days = max_days = duration_range
        
        # Generiere Daten für nächste 6 Monate
        start_date = datetime.now() + timedelta(days=7)  # Nächste Woche
        
        for weeks_ahead in range(0, 24):  # 6 Monate
            for duration in range(min_days, max_days + 1):
                check_in = start_date + timedelta(weeks=weeks_ahead)
                check_out = check_in + timedelta(days=duration)
                
                candidates.append({
                    "check_in": check_in.strftime("%Y-%m-%d"),
                    "check_out": check_out.strftime("%Y-%m-%d"),
                    "duration_days": duration
                })
        
        return candidates[:20]  # Limitiere auf 20 Kandidaten
    
    async def _calculate_date_score(self, destination_info: Dict, date_range: Dict, 
                                  parsed_query: Dict) -> Dict[str, Any]:
        """Bewertet Datum basierend auf verschiedenen Faktoren"""
        
        # Basis-Score
        score = {
            "total": 50.0,
            "breakdown": {
                "seasonal": 0,
                "price_trend": 0,
                "weather": 0,
                "events": 0,
                "demand": 0
            }
        }
        
        check_in_date = datetime.strptime(date_range["check_in"], "%Y-%m-%d")
        
        # Saisonaler Score
        score["breakdown"]["seasonal"] = self._calculate_seasonal_score(
            destination_info, check_in_date, parsed_query["travel_type"]
        )
        
        # Preis-Trend Score (simuliert)
        score["breakdown"]["price_trend"] = self._estimate_price_trend(
            destination_info, check_in_date
        )
        
        # Wetter-Score (könnte mit echter API erweitert werden)
        score["breakdown"]["weather"] = self._estimate_weather_score(
            destination_info, check_in_date
        )
        
        # Events-Score (könnte mit Event-APIs erweitert werden)
        score["breakdown"]["events"] = await self._estimate_events_score(
            destination_info, check_in_date, parsed_query
        )
        
        # Nachfrage-Score
        score["breakdown"]["demand"] = self._estimate_demand_score(check_in_date)
        
        # Gesamtscore berechnen
        weights = {"seasonal": 0.2, "price_trend": 0.3, "weather": 0.2, "events": 0.2, "demand": 0.1}
        
        weighted_score = sum(
            score["breakdown"][factor] * weight 
            for factor, weight in weights.items()
        )
        
        score["total"] = max(0, min(100, 50 + weighted_score))
        
        return score
    
    def _calculate_seasonal_score(self, destination_info: Dict, date: datetime, travel_type: str) -> float:
        """Berechnet saisonalen Score"""
        
        month = date.month
        destination = destination_info.get("city", "Unknown")
        
        # Vereinfachte saisonale Bewertung
        seasonal_scores = {
            "Italien": {
                "romantic": {12: 15, 1: 10, 2: 10, 3: 20, 4: 25, 5: 30, 6: 35, 7: 20, 8: 15, 9: 30, 10: 25, 11: 20},
                "leisure": {12: 10, 1: 5, 2: 10, 3: 25, 4: 30, 5: 35, 6: 40, 7: 35, 8: 30, 9: 35, 10: 30, 11: 15}
            }
        }
        
        return seasonal_scores.get(destination, {}).get(travel_type, {}).get(month, 15)
    
    def _estimate_price_trend(self, destination_info: Dict, date: datetime) -> float:
        """Schätzt Preis-Trend für das Datum"""
        
        month = date.month
        
        # Hochsaison = schlechterer Score
        high_season_months = [6, 7, 8, 12]  # Sommer + Dezember
        
        if month in high_season_months:
            return -15  # Höhere Preise
        else:
            return 10   # Niedrigere Preise
    
    def _estimate_weather_score(self, destination_info: Dict, date: datetime) -> float:
        """Schätzt Wetter-Score"""
        
        month = date.month
        destination = destination_info.get("city", "Unknown")
        
        # Vereinfachte Wetter-Bewertung
        weather_scores = {
            "Italien": {12: 5, 1: 0, 2: 5, 3: 15, 4: 20, 5: 25, 6: 30, 7: 25, 8: 20, 9: 25, 10: 20, 11: 10}
        }
        
        return weather_scores.get(destination, {}).get(month, 10)
    
    async def _estimate_events_score(self, destination_info: Dict, date: datetime, parsed_query: Dict) -> float:
        """Schätzt Events-Score (könnte mit echter API erweitert werden)"""
        
        # Hier könnte eine echte Event-API Integration stehen
        # Für Demo: Simuliere basierend auf Monat und Reisetyp
        
        month = date.month
        travel_type = parsed_query["travel_type"]
        
        if travel_type == "romantic" and month in [2, 6, 12]:  # Valentine's, Hochzeit, Weihnachten
            return 15
        elif travel_type == "cultural" and month in [3, 4, 5, 9, 10]:  # Museumsaison
            return 10
        
        return 5  # Default
    
    def _estimate_demand_score(self, date: datetime) -> float:
        """Schätzt Nachfrage-Score basierend auf Timing"""
        
        # Wochenenden = höhere Nachfrage = schlechterer Score
        if date.weekday() >= 5:  # Samstag/Sonntag
            return -5
        else:
            return 5
    
    async def _perform_multi_search(self, origin: str, destination_info: Dict, 
                                  optimized_dates: List[Dict], parsed_query: Dict) -> Dict[str, Any]:
        """Führt Suche für mehrere optimierte Daten durch"""
        
        all_results = []
        
        # Nutze deine bestehenden Services
        for date_option in optimized_dates[:3]:  # Top 3 Daten
            try:
                # Parallel: Flüge und Hotels suchen
                flights, hotels = await asyncio.gather(
                    self.flight_service.search_flights(
                        origin=origin,
                        destination=destination_info.get("airport_code", destination_info["city"]),
                        outbound_date=date_option["check_in"],
                        return_date=date_option["check_out"]
                    ),
                    self.hotel_service.search_hotels(
                        destination=destination_info["city"],
                        check_in=date_option["check_in"],
                        check_out=date_option["check_out"]
                    )
                )
                
                # Nutze deine bestehende Combination Logic
                combinations = await self.combination_engine.generate_combinations(
                    flights, hotels, parsed_query.get("budget_max")
                )
                
                all_results.append({
                    "date_option": date_option,
                    "flights": flights,
                    "hotels": hotels,
                    "combinations": combinations
                })
                
            except Exception as e:
                print(f"Fehler bei Suche für {date_option}: {e}")
                continue
        
        return {
            "search_results": all_results,
            "total_combinations": sum(len(r["combinations"]) for r in all_results)
        }
    
    async def _generate_smart_recommendations(self, search_results: Dict, 
                                            parsed_query: Dict) -> Dict[str, Any]:
        """Generiert intelligente Empfehlungen mit LLM"""
        
        # Bereite Daten für LLM auf
        summary_data = self._prepare_summary_for_llm(search_results, parsed_query)
        
        # LLM Prompt für Empfehlungen
        prompt = f"""
        Basierend auf den Suchergebnissen, generiere personalisierte Reiseempfehlungen:
        
        Ursprüngliche Anfrage: {parsed_query}
        Suchergebnisse: {summary_data}
        
        Bitte erstelle eine strukturierte Empfehlung mit:
        1. Der besten Option mit Begründung
        2. Alternative Optionen
        3. Personalisierte Tipps basierend auf dem Reisetyp
        4. Budgetoptimierung wenn möglich
        
        Antworte in natürlicher, beratender Sprache.
        """
        
        try:
            recommendations = await self._call_llm_via_mcp(prompt)
            return {"llm_recommendations": recommendations}
        except:
            # Fallback: Regel-basierte Empfehlungen
            return self._generate_fallback_recommendations(search_results, parsed_query)
    
    def _prepare_summary_for_llm(self, search_results: Dict, parsed_query: Dict) -> str:
        """Bereitet Zusammenfassung für LLM vor"""
        
        if not search_results.get("search_results"):
            return "Keine Suchergebnisse verfügbar"
        
        # Finde beste Option
        best_result = search_results["search_results"][0]
        best_combo = best_result["combinations"][0] if best_result["combinations"] else None
        
        if not best_combo:
            return "Keine gültigen Kombinationen gefunden"
        
        summary = f"""
        Beste gefundene Option:
        - Datum: {best_result["date_option"]["check_in"]} bis {best_result["date_option"]["check_out"]}
        - Flug: {best_combo["flight"].get("airline", "N/A")} für {best_combo["flight"].get("price_eur", "N/A")}€
        - Hotel: {best_combo["hotel"].get("name", "N/A")} ({best_combo["hotel"].get("rating", "N/A")}⭐) für {best_combo["hotel"].get("price_per_night", "N/A")}€/Nacht
        - Gesamtkosten: {best_combo.get("total_price", "N/A")}€
        - Alternativen: {len(search_results["search_results"])} weitere Optionen verfügbar
        """
        
        return summary
    
    def _generate_fallback_recommendations(self, search_results: Dict, parsed_query: Dict) -> Dict[str, Any]:
        """Fallback-Empfehlungen ohne LLM"""
        
        return {
            "best_option": "Option 1 empfohlen aufgrund von Preis-Leistungs-Verhältnis",
            "alternatives": "Weitere Optionen verfügbar mit verschiedenen Daten",
            "tips": f"Für {parsed_query['travel_type']} Reisen empfehlen wir hochbewertete Hotels",
            "budget_advice": "Prüfen Sie flexible Daten für bessere Preise"
        }