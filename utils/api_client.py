# utils/api_client.py - Unified API Client with Retry Logic
from typing import Dict, Any, List, Optional
import asyncio
import httpx
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    base_delay: float = 2.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_backoff: bool = True
    timeout: float = 300.0  # Request timeout in seconds

class ApifyClient:
    """Unified Apify API Client with robust retry logic"""
    
    def __init__(self, api_token: str, retry_config: Optional[RetryConfig] = None):
        self.api_token = api_token
        self.retry_config = retry_config or RetryConfig()
        self.base_url = "https://api.apify.com/v2/acts"
    
    async def call_actor(
        self, 
        actor_name: str, 
        input_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Call an Apify actor with retry logic
        
        Args:
            actor_name: Name of the Apify actor (e.g., "jupri~skyscanner-flight")
            input_data: Input data for the actor
            options: Additional options (e.g., maxItems, timeout)
            
        Returns:
            List of results from the actor
            
        Raises:
            ApiClientError: When all retries are exhausted
        """
        if not self.api_token:
            raise ApiClientError("No APIFY_TOKEN configured")
        
        # Prepare payload
        payload = input_data.copy()
        if options:
            payload["options"] = options
        
        url = f"{self.base_url}/{actor_name}/run-sync-get-dataset-items"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        logger.info(f"Calling actor: {actor_name}")
        logger.debug(f"Input data: {input_data}")
        
        last_exception = None
        
        for attempt in range(self.retry_config.max_retries):
            try:
                # Calculate delay for this attempt
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    logger.info(f"Retrying in {delay:.1f}s (attempt {attempt + 1}/{self.retry_config.max_retries})")
                    await asyncio.sleep(delay)
                
                # Make the API call
                async with httpx.AsyncClient(timeout=self.retry_config.timeout) as client:
                    logger.debug(f"Making API request to {url}")
                    response = await client.post(url, headers=headers, json=payload)
                    
                    # Log response status
                    logger.debug(f"Response status: {response.status_code}")
                    
                    # Check for success
                    if response.status_code in [200, 201]:
                        data = response.json()
                        logger.info(f"Actor {actor_name} returned {len(data)} items")
                        return data
                    
                    # Handle API errors
                    error_msg = f"API returned status {response.status_code}"
                    if response.text:
                        error_msg += f": {response.text[:200]}"
                    
                    logger.warning(f"API error on attempt {attempt + 1}: {error_msg}")
                    
                    # Decide whether to retry based on status code
                    if not self._should_retry(response.status_code):
                        raise ApiClientError(f"Non-retryable error: {error_msg}")
                    
                    last_exception = ApiClientError(error_msg)
                    
            except asyncio.TimeoutError as e:
                error_msg = f"Request timeout after {self.retry_config.timeout}s"
                logger.warning(f"Timeout on attempt {attempt + 1}: {error_msg}")
                last_exception = ApiClientError(error_msg)
                
            except httpx.RequestError as e:
                error_msg = f"Request error: {str(e)}"
                logger.warning(f"Request error on attempt {attempt + 1}: {error_msg}")
                last_exception = ApiClientError(error_msg)
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error on attempt {attempt + 1}: {error_msg}")
                last_exception = ApiClientError(error_msg)
        
        # All retries exhausted
        final_error = f"All {self.retry_config.max_retries} attempts failed for actor {actor_name}"
        if last_exception:
            final_error += f". Last error: {last_exception}"
        
        logger.error(final_error)
        raise ApiClientError(final_error)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff"""
        if not self.retry_config.exponential_backoff:
            return self.retry_config.base_delay
        
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = self.retry_config.base_delay * (2 ** attempt)
        return min(delay, self.retry_config.max_delay)
    
    def _should_retry(self, status_code: int) -> bool:
        """Determine if we should retry based on HTTP status code"""
        # Retry on server errors and rate limiting
        retryable_codes = {500, 502, 503, 504, 429}
        return status_code in retryable_codes
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if the API is accessible"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.apify.com/v2/users/me",
                    headers={"Authorization": f"Bearer {self.api_token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    return {
                        "status": "healthy",
                        "message": f"Connected as {user_data.get('username', 'Unknown')}",
                        "user_id": user_data.get('id')
                    }
                else:
                    return {
                        "status": "error", 
                        "message": f"API returned {response.status_code}"
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}"
            }

class ApiClientError(Exception):
    """Custom exception for API client errors"""
    pass

# Factory function for easy client creation
def create_apify_client(api_token: str, **retry_kwargs) -> ApifyClient:
    """Create an Apify client with optional retry configuration"""
    retry_config = RetryConfig(**retry_kwargs) if retry_kwargs else RetryConfig()
    return ApifyClient(api_token, retry_config)