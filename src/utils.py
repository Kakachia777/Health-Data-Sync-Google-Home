import time
import logging
from functools import wraps
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, calls_per_minute=30):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = datetime.now()
            # Remove calls older than 1 minute
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < timedelta(minutes=1)]
            
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0]).seconds
                if sleep_time > 0:
                    logging.info(f"Rate limit reached. Waiting {sleep_time} seconds")
                    time.sleep(sleep_time)
            
            self.calls.append(now)
            return func(*args, **kwargs)
        return wrapper

def retry_on_exception(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        sleep_time = delay * (2 ** attempt)  # Exponential backoff
                        logging.warning(
                            f"Attempt {attempt + 1}/{retries} failed: {str(e)}. "
                            f"Retrying in {sleep_time} seconds..."
                        )
                        time.sleep(sleep_time)
            
            logging.error(f"All {retries} attempts failed. Last error: {str(last_exception)}")
            raise last_exception
        return wrapper
    return decorator

class HealthMetric:
    def __init__(self, value, timestamp, metric_type, unit, additional_data=None):
        self.value = value
        self.timestamp = timestamp
        self.type = metric_type
        self.unit = unit
        self.additional_data = additional_data or {}
        
    def to_dict(self):
        return {
            'value': self.value,
            'timestamp': self.timestamp,
            'type': self.type,
            'unit': self.unit,
            **self.additional_data
        }
        
    @classmethod
    def from_dict(cls, data):
        additional_data = data.copy()
        for key in ['value', 'timestamp', 'type', 'unit']:
            additional_data.pop(key, None)
        return cls(
            value=data['value'],
            timestamp=data['timestamp'],
            metric_type=data['type'],
            unit=data['unit'],
            additional_data=additional_data
        ) 