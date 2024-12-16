import os
import logging
from google.oauth2 import service_account
from google.cloud import texttospeech
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2
from google.assistant.embedded.v1alpha2 import embedded_assistant_pb2_grpc
import grpc
from typing import Optional

class GoogleHomeHandler:
    def __init__(self, project_id: str, device_id: str, language_code: str = 'en-US'):
        self.project_id = project_id
        self.device_id = device_id
        self.language_code = language_code
        self.credentials = None
        self.tts_client = None
        self.assistant_client = None
        self.setup_clients()
        
    def setup_clients(self):
        """Initialize Google clients"""
        try:
            # Load credentials from service account file
            self.credentials = service_account.Credentials.from_service_account_file(
                'config/google_home_credentials.json',
                scopes=['https://www.googleapis.com/auth/assistant-sdk-prototype']
            )
            
            # Initialize Text-to-Speech client
            self.tts_client = texttospeech.TextToSpeechClient()
            
            # Initialize Assistant client
            channel = grpc.secure_channel('embeddedassistant.googleapis.com', 
                                        grpc.ssl_channel_credentials())
            self.assistant_client = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(channel)
            
            logging.info("Successfully initialized Google Home clients")
            
        except Exception as e:
            logging.error(f"Failed to initialize Google Home clients: {str(e)}")
            raise
            
    def _convert_text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using Google TTS"""
        try:
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logging.error(f"Failed to convert text to speech: {str(e)}")
            return None
            
    def send_notification(self, message: str, priority: str = 'normal') -> bool:
        """Send notification to Google Home device"""
        try:
            # Convert notification to speech
            audio_content = self._convert_text_to_speech(message)
            if not audio_content:
                return False
                
            # Create assistant request
            config = embedded_assistant_pb2.AssistConfig(
                audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                    encoding='LINEAR16',
                    sample_rate_hertz=16000,
                    volume_percentage=100,
                ),
                device_config=embedded_assistant_pb2.DeviceConfig(
                    device_id=self.device_id,
                    device_model_id=f"{self.project_id}-health-monitor"
                ),
                dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                    language_code=self.language_code,
                    conversation_state=None,
                    is_new_conversation=True,
                ),
            )
            
            # Create request generator
            def request_generator():
                yield embedded_assistant_pb2.AssistRequest(config=config)
                yield embedded_assistant_pb2.AssistRequest(audio_in=audio_content)
                
            # Send request
            responses = self.assistant_client.Assist(request_generator())
            
            # Process response
            for response in responses:
                if response.dialog_state_out.supplemental_display_text:
                    logging.info(f"Assistant response: {response.dialog_state_out.supplemental_display_text}")
                    
            return True
            
        except Exception as e:
            logging.error(f"Failed to send Google Home notification: {str(e)}")
            return False
            
    def format_health_alert(self, alert_data: dict) -> str:
        """Format health alert for voice notification"""
        alert_type = alert_data.get('type', 'health')
        message = alert_data.get('message', '')
        
        if alert_type == 'blood_pressure':
            return f"Health Alert: Your blood pressure reading is {message}"
        elif alert_type == 'heart_rate':
            return f"Health Alert: Your heart rate is {message}"
        elif alert_type == 'weight':
            return f"Health Alert: Your weight measurement is {message}"
        elif alert_type == 'sleep':
            return f"Health Alert: {message}"
        else:
            return f"Health Alert: {message}" 