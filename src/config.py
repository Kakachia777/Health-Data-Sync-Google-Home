import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load environment variables from config/.env
        load_dotenv(os.path.join('config', '.env'))
        
        # Withings credentials
        self.withings_client_id = os.getenv('WITHINGS_CLIENT_ID')
        self.withings_client_secret = os.getenv('WITHINGS_CLIENT_SECRET')
        self.withings_callback_uri = os.getenv('WITHINGS_CALLBACK_URI')
        
        # Omron credentials
        self.omron_client_id = os.getenv('OMRON_CLIENT_ID')
        self.omron_client_secret = os.getenv('OMRON_CLIENT_SECRET')
        
        # Google Calendar settings
        self.google_calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
        
    def validate(self):
        """Validate that all required configuration is present"""
        required_vars = [
            'withings_client_id',
            'withings_client_secret',
            'withings_callback_uri',
            'omron_client_id',
            'omron_client_secret',
            'google_calendar_id'
        ]
        
        missing = []
        for var in required_vars:
            if not getattr(self, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        return True 