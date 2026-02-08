"""
API utility functions for Museum Guide MVP.
"""

import asyncio
import functools
from typing import TypeVar, Callable, Any

T = TypeVar('T')


def async_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying async functions.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff

            raise last_exception

        return wrapper
    return decorator


def handle_api_error(response: Any) -> dict:
    """
    Handle API error responses uniformly.

    Args:
        response: API response object

    Returns:
        dict with error information
    """
    if hasattr(response, 'status_code'):
        return {
            "success": False,
            "error_code": response.status_code,
            "error_message": getattr(response, 'message', 'Unknown error')
        }
    return {
        "success": False,
        "error_message": str(response)
    }


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: float = 2.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum calls per second
        """
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        async with self._lock:
            current = asyncio.get_event_loop().time()
            elapsed = current - self.last_call

            if elapsed < self.min_interval:
                await asyncio.sleep(self.min_interval - elapsed)

            self.last_call = asyncio.get_event_loop().time()
