import requests
from datetime import datetime
import logging
from .utils import retry_on_exception, RateLimiter, HealthMetric

class OmronHandler:
    def __init__(self, config):
        self.config = config
        self.base_url = "https://api-omronwellness.com/v1"
        self.access_token = None
        self.rate_limiter = RateLimiter(calls_per_minute=30)
        
    def authenticate(self, access_token):
        """Set up authentication token"""
        self.access_token = access_token
        
    @retry_on_exception(retries=3, delay=1)
    @RateLimiter(calls_per_minute=30)
    def _make_request(self, endpoint, method='GET', params=None):
        """Make authenticated request to Omron API"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error making Omron API request: {str(e)}")
            raise
            
    @retry_on_exception(retries=3, delay=1)
    def get_blood_pressure_data(self):
        """Fetch latest blood pressure readings"""
        try:
            data = self._make_request('bloodpressure/readings')
            if not data:
                return []
                
            formatted_data = []
            for reading in data.get('readings', []):
                metric = HealthMetric(
                    value={'systolic': reading['systolic'], 'diastolic': reading['diastolic']},
                    timestamp=datetime.fromisoformat(reading['datetime']),
                    metric_type='blood_pressure',
                    unit='mmHg',
                    additional_data={
                        'pulse': reading.get('pulse'),
                        'irregular': reading.get('irregular', False)
                    }
                )
                formatted_data.append(metric.to_dict())
            
            return formatted_data
        except Exception as e:
            logging.error(f"Error processing blood pressure data: {str(e)}")
            raise
            
    @retry_on_exception(retries=3, delay=1)
    def get_heart_rate_data(self):
        """Fetch latest heart rate readings"""
        try:
            data = self._make_request('heartrate/readings')
            if not data:
                return []
                
            formatted_data = []
            for reading in data.get('readings', []):
                metric = HealthMetric(
                    value=reading['value'],
                    timestamp=datetime.fromisoformat(reading['datetime']),
                    metric_type='heart_rate',
                    unit='bpm',
                    additional_data={
                        'activity_level': reading.get('activity_level'),
                        'measurement_source': reading.get('source', 'device')
                    }
                )
                formatted_data.append(metric.to_dict())
            
            return formatted_data
        except Exception as e:
            logging.error(f"Error processing heart rate data: {str(e)}")
            raise 