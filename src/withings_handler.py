from withings_api import WithingsAuth, WithingsApi
from datetime import datetime
import logging
from .utils import retry_on_exception, RateLimiter, HealthMetric

class WithingsHandler:
    def __init__(self, config):
        self.config = config
        self.auth = WithingsAuth(
            client_id=config.withings_client_id,
            client_secret=config.withings_client_secret,
            callback_uri=config.withings_callback_uri,
            scope=("user.metrics", "user.activity")
        )
        self.client = None
        self.rate_limiter = RateLimiter(calls_per_minute=30)
        
    def authenticate(self, access_token):
        """Initialize the Withings API client with access token"""
        self.client = WithingsApi(access_token)
        
    @retry_on_exception(retries=3, delay=1)
    @RateLimiter(calls_per_minute=30)
    def get_weight_data(self):
        """Fetch latest weight measurements"""
        try:
            measures = self.client.measure_get_meas()
            weight_data = []
            
            for measure in measures.measures:
                if measure.type == 1:  # Weight measurement
                    metric = HealthMetric(
                        value=measure.value * 0.001,  # Convert to kg
                        timestamp=datetime.fromtimestamp(measure.date),
                        metric_type='weight',
                        unit='kg'
                    )
                    weight_data.append(metric.to_dict())
            
            return weight_data
        except Exception as e:
            logging.error(f"Error fetching weight data: {str(e)}")
            raise
            
    @retry_on_exception(retries=3, delay=1)
    @RateLimiter(calls_per_minute=30)
    def get_sleep_data(self):
        """Fetch latest sleep data"""
        try:
            end_date = datetime.now()
            start_date = end_date.replace(hour=0, minute=0, second=0)
            
            sleep_data = self.client.sleep_get(startdate=start_date, enddate=end_date)
            formatted_data = []
            
            for series in sleep_data.series:
                metric = HealthMetric(
                    value=series.state,
                    timestamp=datetime.fromtimestamp(series.startdate),
                    metric_type='sleep',
                    unit='state',
                    additional_data={
                        'start': datetime.fromtimestamp(series.startdate),
                        'end': datetime.fromtimestamp(series.enddate)
                    }
                )
                formatted_data.append(metric.to_dict())
            
            return formatted_data
        except Exception as e:
            logging.error(f"Error fetching sleep data: {str(e)}")
            raise 