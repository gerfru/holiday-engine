# services/crowd_sourced_service.py - CLEAN VERSION (No Mock Data)
"""
Clean crowd-sourced travel tips service
Only real data from Reddit - no fake mock data
"""

import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class SimpleCrowdService:
    """
    Clean crowd-sourced travel tips service
    Only returns REAL data from Reddit - no mock/fake data
    """
    
    def __init__(self):
        self.cache = {}  # Simple in-memory cache
        self.session = None
    
    async def get_travel_tips(self, destination: str) -> List[Dict[str, Any]]:
        """
        Get travel tips for destination - ONLY REAL DATA
        
        Args:
            destination: Destination city name
            
        Returns:
            List of REAL travel tips from Reddit (empty if none found)
        """
        cache_key = f"tips_{destination.lower()}"
        
        # Check cache first
        if cache_key in self.cache:
            cached_tips, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(hours=24):
                logger.info(f"Using cached tips for {destination}")
                return cached_tips
        
        try:
            # Try Reddit JSON API (no authentication needed)
            tips = await self._fetch_reddit_tips(destination)
            
            # Cache results (even if empty)
            self.cache[cache_key] = (tips, datetime.now())
            
            logger.info(f"Found {len(tips)} REAL tips for {destination}")
            return tips
            
        except Exception as e:
            logger.error(f"Error getting tips for {destination}: {e}")
            # Return empty list - NO FAKE DATA
            return []
    
    async def _fetch_reddit_tips(self, destination: str) -> List[Dict[str, Any]]:
        """
        Fetch REAL tips from Reddit JSON API
        """
        tips = []
        
        # Search multiple subreddits for better coverage
        subreddits = ['travel', 'solotravel', 'backpacking', 'digitalnomad']
        
        for subreddit in subreddits:
            try:
                subreddit_tips = await self._search_subreddit(subreddit, destination)
                tips.extend(subreddit_tips)
                
                # Small delay to be respectful
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.warning(f"Failed to search r/{subreddit}: {e}")
                continue
        
        # Remove duplicates and sort by relevance
        tips = self._deduplicate_tips(tips)
        tips.sort(key=lambda t: t['upvotes'], reverse=True)
        
        return tips[:20]  # Max 20 tips
    
    async def _search_subreddit(self, subreddit: str, destination: str) -> List[Dict[str, Any]]:
        """Search a specific subreddit for destination tips"""
        tips = []
        
        try:
            # Reddit JSON API endpoint
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {
                'q': destination,
                'limit': 10,
                'sort': 'relevance',
                't': 'year'  # Posts from last year
            }
            
            headers = {
                'User-Agent': 'HolidayEngine/2.1 (travel-search-platform)'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        tips = self._parse_reddit_data(data, destination, subreddit)
                    else:
                        logger.warning(f"Reddit API returned status {response.status} for r/{subreddit}")
                        
        except Exception as e:
            logger.warning(f"Error searching r/{subreddit}: {e}")
        
        return tips
    
    def _parse_reddit_data(self, data: Dict[str, Any], destination: str, subreddit: str) -> List[Dict[str, Any]]:
        """
        Parse Reddit JSON response into clean tip objects
        """
        tips = []
        
        try:
            posts = data.get('data', {}).get('children', [])
            
            for post in posts:
                post_data = post.get('data', {})
                
                # Extract post content
                title = post_data.get('title', '')
                text = post_data.get('selftext', '')
                upvotes = post_data.get('ups', 0)
                permalink = post_data.get('permalink', '')
                author = post_data.get('author', 'Anonymous')
                
                # Skip if no useful content
                if not title and not text:
                    continue
                
                # Skip deleted/removed posts
                if author in ['[deleted]', '[removed]']:
                    continue
                
                # Combine title and text
                full_content = f"{title}. {text}".strip()
                
                # Filter for relevance and quality
                if self._is_relevant_tip(full_content, destination):
                    tip = {
                        'tip': self._clean_text(full_content),
                        'upvotes': upvotes,
                        'source': f'r/{subreddit}',
                        'category': self._categorize_tip(full_content),
                        'url': f"https://reddit.com{permalink}" if permalink else '',
                        'author': author if author != 'Anonymous' else f'r/{subreddit} user'
                    }
                    tips.append(tip)
        
        except Exception as e:
            logger.warning(f"Error parsing Reddit data from r/{subreddit}: {e}")
        
        return tips
    
    def _is_relevant_tip(self, text: str, destination: str) -> bool:
        """
        Check if content is relevant and useful travel tip
        """
        text_lower = text.lower()
        destination_lower = destination.lower()
        
        # Must mention destination
        if destination_lower not in text_lower:
            return False
        
        # Must be substantial content
        if len(text) < 50:
            return False
        
        # Must contain travel-related keywords
        travel_keywords = [
            'tip', 'recommend', 'visit', 'avoid', 'restaurant', 'hotel', 
            'attraction', 'museum', 'food', 'eat', 'stay', 'transport',
            'metro', 'bus', 'taxi', 'worth', 'best', 'good', 'bad',
            'experience', 'advice', 'suggestion', 'guide'
        ]
        
        if not any(keyword in text_lower for keyword in travel_keywords):
            return False
        
        # Filter out obvious spam/promotional content
        spam_keywords = [
            'click here', 'buy now', 'discount', 'promo', 'affiliate',
            'sponsored', 'advertisement', 'check out my', 'visit my'
        ]
        
        if any(spam in text_lower for spam in spam_keywords):
            return False
        
        # Filter out low-quality content
        if text_lower.count('http') > 2:  # Too many links
            return False
        
        return True
    
    def _categorize_tip(self, text: str) -> str:
        """
        Categorize tip based on content
        """
        text_lower = text.lower()
        
        # Category keywords
        categories = {
            'restaurants': ['restaurant', 'food', 'eat', 'meal', 'dining', 'cafe', 'bar', 'tapas', 'cuisine'],
            'activities': ['museum', 'attraction', 'visit', 'see', 'tour', 'show', 'park', 'beach', 'activity'],
            'warnings': ['avoid', 'scam', 'dangerous', 'careful', 'warning', 'don\'t', 'pickpocket', 'theft'],
            'transport': ['metro', 'bus', 'taxi', 'train', 'airport', 'transport', 'uber', 'walk'],
            'accommodation': ['hotel', 'stay', 'accommodation', 'airbnb', 'booking', 'room', 'hostel']
        }
        
        # Find best matching category
        best_category = 'general'
        best_score = 0
        
        for category, keywords in categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > best_score:
                best_score = score
                best_category = category
        
        return best_category
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and format text content
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove Reddit formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove italic
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        # Limit length
        if len(text) > 400:
            # Find a good breaking point
            sentences = text.split('.')
            result = ""
            for sentence in sentences:
                if len(result + sentence) < 350:
                    result += sentence + "."
                else:
                    break
            text = result.strip()
            if not text.endswith('.'):
                text += "..."
        
        return text.strip()
    
    def _deduplicate_tips(self, tips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate tips based on content similarity
        """
        unique_tips = []
        seen_content = set()
        
        for tip in tips:
            # Create content fingerprint
            content_key = tip['tip'][:100].lower().strip()
            content_key = re.sub(r'\s+', ' ', content_key)
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_tips.append(tip)
        
        return unique_tips


# FastAPI Router - NO CHANGES NEEDED
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()
crowd_service = SimpleCrowdService()

@router.get("/travel-tips/{destination}")
async def get_travel_tips(destination: str):
    """
    Get REAL travel tips for destination from Reddit
    Returns empty list if no real tips found
    """
    try:
        tips = await crowd_service.get_travel_tips(destination)
        
        return {
            'destination': destination,
            'tips': tips,
            'count': len(tips),
            'source': 'reddit-only',
            'note': 'Only real community tips - no mock data'
        }
        
    except Exception as e:
        logger.error(f"Error in travel tips endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error fetching travel tips")

@router.get("/travel-warnings/{destination}")
async def get_travel_warnings(destination: str):
    """
    Get travel warnings for destination from REAL data only
    """
    try:
        tips = await crowd_service.get_travel_tips(destination)
        warnings = [tip for tip in tips if tip['category'] == 'warnings']
        
        return {
            'destination': destination,
            'warnings': warnings,
            'count': len(warnings),
            'source': 'reddit-only'
        }
        
    except Exception as e:
        logger.error(f"Error in travel warnings endpoint: {e}")
        raise HTTPException(status_code=500, detail="Error fetching travel warnings")


# Debug function for testing
async def debug_reddit_tips():
    """Debug function to test real Reddit tips"""
    service = SimpleCrowdService()
    
    destinations = ['Barcelona', 'Paris', 'Tokyo', 'New York']
    
    for dest in destinations:
        print(f"\n🔍 Testing {dest}:")
        tips = await service.get_travel_tips(dest)
        print(f"Found {len(tips)} REAL tips")
        
        for i, tip in enumerate(tips[:3]):
            print(f"  {i+1}. [{tip['category']}] {tip['tip'][:60]}...")
            print(f"     👍 {tip['upvotes']} | {tip['source']}")

if __name__ == "__main__":
    # Test the service
    asyncio.run(debug_reddit_tips())