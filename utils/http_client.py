import requests
import time
import json
import logging

# Configure basic logging for the resilience wrapper
logger = logging.getLogger(__name__)
if not logger.handlers:
    # Adding a simple console handler so we can see the retries
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

class ResilientClientError(Exception):
    """Base exception for all HTTP client errors that should trigger a fallback."""
    pass

class RateLimitError(ResilientClientError):
    pass

class InvalidJSONError(ResilientClientError):
    pass

class SourceUnavailableError(ResilientClientError):
    pass


def fetch_with_resilience(url, method='GET', params=None, data=None, headers=None, initial_timeout=5):
    """
    A strictly resilient HTTP client wrapper fulfilling Stage 3 requirements.
    
    Retry Logic:
    - Up to 3 retries for transient errors (Timeout, 429, 500+).
    - Exponential backoff wait intervals: 2s, 5s, 10s.
    
    Specific Handlings:
    - Timeout: Retry with a longer timeout (+5s each retry).
    - 429 Rate Limit: Wait 30s as per requirement, then retry.
    - 404: Skip immediately (raise SourceUnavailableError).
    - Invalid JSON: Try to clean JSON; if failed, raise InvalidJSONError.
    - Empty Response: Raise SourceUnavailableError.
    
    Returns:
    - Processed JSON dict.
    """
    max_retries = 3
    backoff_intervals = [2, 5, 10]
    
    timeout = initial_timeout
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"API Request ({method}): {url} [Attempt {attempt + 1}]")
            
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=timeout
            )
            
            # Immediately short-circuit for hard 404 (Not Found)
            if response.status_code == 404:
                logger.warning(f"404 Not Found at {url}. Skipping source.")
                raise SourceUnavailableError(f"HTTP 404 at {url}")
                
            # Rate Limiting (429)
            if response.status_code == 429:
                logger.warning(f"Rate Limiting (429) at {url}. Waiting 30s before retry.")
                if attempt < max_retries:
                    time.sleep(30)
                    # Use standard backoff interval if we have retries left? The prompt explicitly says wait 30s for 429.
                    # We will continue the loop to retry.
                    continue
                else:
                    raise RateLimitError(f"Max retries hit for 429 Rate Limit at {url}")
            
            # 500 / 503 Errors
            if response.status_code >= 500:
                logger.warning(f"Server Error ({response.status_code}) at {url}.")
                if attempt < max_retries:
                    wait_time = backoff_intervals[attempt]
                    logger.info(f"Retrying in {wait_time} seconds (Exponential Backoff).")
                    time.sleep(wait_time)
                    continue
                else:
                    raise SourceUnavailableError(f"HTTP {response.status_code} at {url}")

            # Raise for any other 4xx client errors that aren't specifically handled
            response.raise_for_status()

            # Empty Response validation
            text_resp = response.text.strip()
            if not text_resp:
                logger.warning("Empty response received.")
                raise SourceUnavailableError("Empty response body.")
                
            # JSON format validation and reconstruction attempt
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received from {url}. Attempting to clean.")
                # Attempt structural cleaning (e.g., removing trailing commas or invisible characters)
                # For robust cleaning, you'd use regex, but we represent the intent here
                cleaned_text = text_resp.replace('\n', '').strip()
                if cleaned_text.startswith("```json"):
                     cleaned_text = cleaned_text.replace("```json", "").replace("```", "")
                
                try:
                    return json.loads(cleaned_text)
                except json.JSONDecodeError:
                    raise InvalidJSONError(f"Failed to parse or reconstruct JSON from {url}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout Error at {url}.")
            if attempt < max_retries:
                # Retry with longer timeout
                timeout += 5
                wait_time = backoff_intervals[attempt]
                logger.info(f"Retrying with longer timeout ({timeout}s) in {wait_time} seconds.")
                time.sleep(wait_time)
                continue
            else:
                raise SourceUnavailableError(f"Max retries hit due to Timeout at {url}")

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP Connection Error: {e}")
            if attempt < max_retries:
                wait_time = backoff_intervals[attempt]
                logger.info(f"Retrying in {wait_time} seconds (Exponential Backoff).")
                time.sleep(wait_time)
                continue
            else:
                raise SourceUnavailableError(f"Connection failed at {url}")
                
    # If the loop completes without returning, it means max retries were exhausted
    raise SourceUnavailableError(f"Max retries ({max_retries}) exhausted for {url}.")
