"""
Exponential backoff with jitter for retry logic
"""
import random
import time

def sleep_backoff(attempt: int, base: float = 2.0, cap: float = 60.0, jitter: float = 0.6):
    """
    Sleep with exponential backoff + full jitter
    
    Args:
        attempt: Retry attempt number (1-indexed)
        base: Backoff base multiplier  
        cap: Maximum delay in seconds
        jitter: Maximum jitter to add (0 to jitter seconds)
    """
    delay = min(cap, (base ** max(0, attempt - 1)))
    jitter_amount = random.uniform(0, jitter)
    total_delay = delay + jitter_amount
    
    print(f"   ⏸️  Backoff: {delay:.1f}s + {jitter_amount:.2f}s jitter = {total_delay:.1f}s")
    time.sleep(total_delay)
    
    return total_delay


def retry_with_backoff(func, max_retries: int = 6, base: float = 2.0, cap: float = 60.0):
    """
    Retry a function with exponential backoff
    
    Args:
        func: Function to retry (should raise exception on failure)
        max_retries: Maximum number of retry attempts
        base: Backoff base multiplier
        cap: Maximum delay in seconds
        
    Returns:
        Result of func() on success
        
    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            print(f"   ⚠️  Attempt {attempt}/{max_retries} failed: {e}")
            
            if attempt < max_retries:
                sleep_backoff(attempt, base=base, cap=cap)
            else:
                print(f"   ❌ All {max_retries} attempts exhausted")
    
    raise last_exception

