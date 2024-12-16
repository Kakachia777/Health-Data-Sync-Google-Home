import logging
import time
import schedule
from datetime import datetime
import os
import sys
from typing import List, Dict, Any
import threading
import asyncio

from config import Config
from withings_handler import WithingsHandler
from omron_handler import OmronHandler
from calendar_handler import CalendarHandler
from utils import retry_on_exception
from advanced_utils import (
    DataAnalyzer,
    CacheManager,
    HealthMetricsAggregator,
    NotificationManager
)
from dashboard import HealthDashboard
from telegram_bot import HealthBot
from google_home_handler import GoogleHomeHandler

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/health_sync.log'),
        logging.StreamHandler()
    ]
)

class HealthSync:
    def __init__(self):
        try:
            # Initialize configuration
            self.config = Config()
            self.config.validate()
            
            # Initialize handlers
            self.withings = WithingsHandler(self.config)
            self.omron = OmronHandler(self.config)
            self.calendar = CalendarHandler(self.config)
            
            # Initialize advanced features
            self.cache = CacheManager(redis_url=os.getenv('REDIS_URL'))
            self.analyzer = DataAnalyzer()
            self.metrics_aggregator = HealthMetricsAggregator()
            self.notification_manager = NotificationManager()
            
            # Initialize notification systems
            self._setup_notification_handlers()
            
            # Track sync status
            self.last_sync_status = {
                'withings_weight': None,
                'withings_sleep': None,
                'omron_bp': None,
                'omron_hr': None
            }
            
            # Data storage
            self.latest_metrics = {}
            self.cached_summary = None
            self.active_alerts = []
            
            # Authenticate with services
            self.authenticate_services()
            
        except Exception as e:
            logging.critical(f"Failed to initialize HealthSync: {str(e)}")
            raise
            
    def _setup_notification_handlers(self):
        """Set up notification handlers based on configuration"""
        # Initialize dashboard
        self.dashboard = HealthDashboard(port=8050)
        
        # Initialize Telegram bot if enabled
        if os.getenv('ENABLE_TELEGRAM', 'false').lower() == 'true':
            self.bot = HealthBot(
                token=os.getenv('TELEGRAM_BOT_TOKEN'),
                health_sync=self
            )
            
        # Initialize Google Home if enabled
        if os.getenv('ENABLE_GOOGLE_HOME', 'true').lower() == 'true':
            self.google_home = GoogleHomeHandler(
                project_id=os.getenv('GOOGLE_HOME_PROJECT_ID'),
                device_id=os.getenv('GOOGLE_HOME_DEVICE_ID'),
                language_code=os.getenv('GOOGLE_HOME_LANGUAGE', 'en-US')
            )
            
    def authenticate_services(self):
        """Authenticate with all services"""
        try:
            self.calendar.authenticate()
            # Note: Withings and Omron tokens should be obtained through their OAuth flow
            # and stored securely. This is a placeholder for the actual implementation.
            logging.info("Successfully authenticated with all services")
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            raise
            
    def get_latest_metrics(self) -> Dict[str, Any]:
        """Get latest health metrics"""
        return self.latest_metrics
        
    def get_alerts(self) -> List[str]:
        """Get active health alerts"""
        return self.active_alerts
        
    def generate_health_summary(self) -> Dict[str, Any]:
        """Generate health metrics summary"""
        if self.cached_summary:
            cache_age = (datetime.now() - self.cached_summary['timestamp']).total_seconds()
            if cache_age < 3600:  # Use cache if less than 1 hour old
                return self.cached_summary
                
        summary = self.metrics_aggregator.generate_health_summary(
            weight_data=self._safe_sync(self.withings.get_weight_data, 'withings_weight'),
            bp_data=self._safe_sync(self.omron.get_blood_pressure_data, 'omron_bp'),
            hr_data=self._safe_sync(self.omron.get_heart_rate_data, 'omron_hr'),
            sleep_data=self._safe_sync(self.withings.get_sleep_data, 'withings_sleep')
        )
        
        self.cached_summary = summary
        return summary
        
    def _safe_sync(self, sync_func: callable, data_type: str) -> List[Dict[str, Any]]:
        """Safely execute a sync function with error handling and caching"""
        try:
            # Check cache first
            cache_key = {'function': data_type, 'date': datetime.now().date().isoformat()}
            cached_data = self.cache.get_cached_data(cache_key)
            if cached_data:
                return cached_data
                
            # Fetch new data
            data = sync_func()
            self.last_sync_status[data_type] = {
                'status': 'success',
                'timestamp': datetime.now(),
                'error': None
            }
            
            # Cache the result
            self.cache.cache_data(cache_key, data)
            return data
            
        except Exception as e:
            self.last_sync_status[data_type] = {
                'status': 'error',
                'timestamp': datetime.now(),
                'error': str(e)
            }
            return []
            
    @retry_on_exception(retries=3, delay=1)
    def sync_health_data(self):
        """Sync all health data to Google Calendar"""
        try:
            # Get all health data
            weight_data = self._safe_sync(
                self.withings.get_weight_data,
                'withings_weight'
            )
            sleep_data = self._safe_sync(
                self.withings.get_sleep_data,
                'withings_sleep'
            )
            bp_data = self._safe_sync(
                self.omron.get_blood_pressure_data,
                'omron_bp'
            )
            hr_data = self._safe_sync(
                self.omron.get_heart_rate_data,
                'omron_hr'
            )
            
            # Update latest metrics
            if weight_data:
                self.latest_metrics['weight'] = weight_data[-1]
            if bp_data:
                self.latest_metrics['blood_pressure'] = bp_data[-1]
            if hr_data:
                self.latest_metrics['heart_rate'] = hr_data[-1]
            if sleep_data:
                self.latest_metrics['sleep'] = sleep_data[-1]
                
            # Generate health summary and check for alerts
            summary = self.metrics_aggregator.generate_health_summary(
                weight_data, bp_data, hr_data, sleep_data
            )
            new_alerts = self.notification_manager.check_health_metrics(summary)
            
            # Update alerts and notify if needed
            if new_alerts != self.active_alerts:
                self.active_alerts = new_alerts
                self._send_alert_notifications()
                
            # Create calendar events
            success_count = 0
            total_count = 0
            
            for data in weight_data + sleep_data + bp_data + hr_data:
                total_count += 1
                try:
                    if self.calendar.create_health_event(data):
                        success_count += 1
                except Exception as e:
                    logging.error(f"Failed to create calendar event: {str(e)}")
                    
            # Log sync statistics
            logging.info(
                f"Health data sync completed. "
                f"Successfully synced {success_count}/{total_count} events"
            )
            
            # Check for persistent errors
            self._check_sync_health()
            
        except Exception as e:
            logging.error(f"Error during health data sync: {str(e)}")
            raise
            
    def _send_alert_notifications(self):
        """Send notifications for new alerts"""
        if not self.active_alerts:
            return
            
        alert_text = "New Health Alerts:\n\n" + "\n".join(self.active_alerts)
        
        # Send to Google Home
        if hasattr(self, 'google_home'):
            for alert in self.active_alerts:
                alert_data = self._parse_alert(alert)
                message = self.google_home.format_health_alert(alert_data)
                self.google_home.send_notification(message)
                
        # Send to Telegram (if enabled)
        if hasattr(self, 'bot'):
            for chat_id in self._get_subscribed_chats():
                asyncio.create_task(self.bot.send_alert(chat_id, alert_text))
                
    def _parse_alert(self, alert: str) -> Dict[str, Any]:
        """Parse alert text into structured data"""
        alert_data = {'message': alert}
        
        if 'blood pressure' in alert.lower():
            alert_data['type'] = 'blood_pressure'
        elif 'heart rate' in alert.lower():
            alert_data['type'] = 'heart_rate'
        elif 'weight' in alert.lower():
            alert_data['type'] = 'weight'
        elif 'sleep' in alert.lower():
            alert_data['type'] = 'sleep'
        else:
            alert_data['type'] = 'health'
            
        return alert_data
                
    def _get_subscribed_chats(self) -> List[int]:
        """Get list of subscribed Telegram chat IDs"""
        # Implement actual chat ID storage/retrieval
        return [123456789]  # Placeholder
        
    def _check_sync_health(self):
        """Check for persistent sync issues"""
        for data_type, status in self.last_sync_status.items():
            if status and status['status'] == 'error':
                logging.warning(
                    f"Persistent sync error for {data_type}: {status['error']}"
                )
                
    def run(self):
        """Run the health sync service"""
        logging.info("Starting Health Sync service")
        
        try:
            # Start dashboard in a separate thread
            dashboard_thread = threading.Thread(
                target=self.dashboard.run,
                daemon=True
            )
            dashboard_thread.start()
            
            # Start Telegram bot in a separate thread (if enabled)
            if hasattr(self, 'bot'):
                bot_thread = threading.Thread(
                    target=self.bot.run,
                    daemon=True
                )
                bot_thread.start()
            
            # Schedule real-time sync
            schedule.every(1).minutes.do(self.sync_health_data)
            
            # Run initial sync
            self.sync_health_data()
            
            # Keep the script running
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("Shutting down Health Sync service")
            sys.exit(0)
        except Exception as e:
            logging.critical(f"Fatal error in Health Sync service: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        health_sync = HealthSync()
        health_sync.run()
    except Exception as e:
        logging.critical(f"Application error: {str(e)}")
        sys.exit(1) 