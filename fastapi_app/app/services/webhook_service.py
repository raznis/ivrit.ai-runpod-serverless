"""
Webhook service for sending notifications
Ported from the original infer.py implementation
"""
import requests
import json
import hmac
import hashlib
import os
import time
import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhook notifications"""
    
    def __init__(self):
        self.webhook_secret = settings.WEBHOOK_SECRET or os.environ.get('IVRIT_WEBHOOK_SECRET', '')
        self.vercel_bypass_token = os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET', '')
    
    def send_webhook(
        self,
        webhook_url: Optional[str],
        recording_id: Optional[str],
        status: str,
        transcription_text: Optional[str] = None,
        error: Optional[str] = None,
        max_attempts: int = 3
    ) -> bool:
        """
        Send webhook notification
        
        Args:
            webhook_url: The URL to send the webhook to
            recording_id: Unique identifier for the recording
            status: Status of the transcription ('started', 'completed', 'error')
            transcription_text: The transcription result (only for 'completed' status)
            error: Error message (only for 'error' status)
            max_attempts: Number of retry attempts
            
        Returns:
            True if webhook was sent successfully, False otherwise
        """
        if not webhook_url:
            return False
        
        payload = {
            'recording_id': recording_id,
            'status': status,
            'timestamp': None
        }
        
        if transcription_text is not None:
            payload['transcription'] = transcription_text
        
        if error is not None:
            payload['error'] = error
        
        headers = {'Content-Type': 'application/json'}
        
        logger.info(f'Sending webhook to {webhook_url}')
        
        # Add Vercel deployment protection bypass header if token is provided
        if self.vercel_bypass_token:
            headers['x-vercel-protection-bypass'] = self.vercel_bypass_token
        
        # Generate HMAC signature if secret is provided
        if self.webhook_secret:
            payload_str = json.dumps(payload)
            signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers['X-Webhook-Signature'] = signature
        
        # Send webhook with retries
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                logger.info(
                    f"Webhook sent successfully to {webhook_url} for recording {recording_id} "
                    f"with status {status} (attempt {attempt}/{max_attempts})"
                )
                return True
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to send webhook to {webhook_url} (attempt {attempt}/{max_attempts}): {str(e)}")
                
            except Exception as e:
                logger.error(f"Unexpected error sending webhook (attempt {attempt}/{max_attempts}): {str(e)}")
            
            # Sleep for 1 second before next attempt (except after the last attempt)
            if attempt < max_attempts:
                time.sleep(1)
        
        return False
