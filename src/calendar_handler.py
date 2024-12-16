from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os
import pickle
import logging
from datetime import datetime, timedelta

class CalendarHandler:
    def __init__(self, config):
        self.config = config
        self.service = None
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.events']
        
    def authenticate(self):
        """Authenticate with Google Calendar API"""
        creds = None
        if os.path.exists('config/token.pickle'):
            with open('config/token.pickle', 'rb') as token:
                creds = pickle.load(token)
                
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'config/credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
                
            with open('config/token.pickle', 'wb') as token:
                pickle.dump(creds, token)
                
        self.service = build('calendar', 'v3', credentials=creds)
        
    def create_health_event(self, data):
        """Create a calendar event for health data"""
        try:
            event_time = data['timestamp']
            
            if data['type'] == 'weight':
                summary = f"Weight: {data['value']}kg"
                description = f"Weight measurement: {data['value']}kg"
            elif data['type'] == 'blood_pressure':
                summary = f"BP: {data['systolic']}/{data['diastolic']}"
                description = f"Blood Pressure: {data['systolic']}/{data['diastolic']} mmHg"
            elif data['type'] == 'heart_rate':
                summary = f"HR: {data['value']} bpm"
                description = f"Heart Rate: {data['value']} beats per minute"
            elif data['type'] == 'sleep':
                summary = f"Sleep: {data['state']}"
                description = f"Sleep state: {data['state']}\nStart: {data['start']}\nEnd: {data['end']}"
                event_time = data['start']
            else:
                raise ValueError(f"Unknown data type: {data['type']}")
                
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': event_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (event_time + timedelta(minutes=1)).isoformat(),
                    'timeZone': 'UTC',
                }
            }
            
            self.service.events().insert(
                calendarId=self.config.google_calendar_id,
                body=event
            ).execute()
            
            logging.info(f"Created calendar event: {summary}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating calendar event: {str(e)}")
            return False 