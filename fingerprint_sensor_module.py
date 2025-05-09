import requests
from typing import Optional, Dict, Any
import json

class FingerPrintSensor:
    def __init__(self, esp_ip_address: str, port: int = 80):
        """Initialize the fingerprint sensor communication module.
        
        Args:
            esp_ip_address (str): IP address of the ESP32
            port (int): Port number (default is 80)
        """
        self.base_url = f"http://{esp_ip_address}:{port}"
        self.is_connected = False

    def connect(self) -> bool:
        """Test connection to the ESP32."""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=5)
            self.is_connected = response.status_code == 200
            return self.is_connected
        except requests.RequestException:
            self.is_connected = False
            return False

    def initialize_sensor(self) -> bool:
        """Initialize the fingerprint sensor."""
        try:
            response = requests.post(
                f"{self.base_url}/init",
                json={"command": "initialize"},
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def enroll_finger(self, finger_id: int) -> Dict[str, Any]:
        """Enroll a new fingerprint.
        
        Args:
            finger_id (int): ID to assign to the new fingerprint
            
        Returns:
            Dict containing success status and message
        """
        try:
            response = requests.post(
                f"{self.base_url}/enroll",
                json={"finger_id": finger_id},
                timeout=30
            )
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}

    def verify_finger(self) -> Dict[str, Any]:
        """Verify a fingerprint and get its ID if found.
        
        Returns:
            Dict containing success status, finger_id if found, and message
        """
        try:
            response = requests.post(
                f"{self.base_url}/verify",
                json={"command": "verify"},
                timeout=10
            )
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "message": str(e), "finger_id": None}

    def delete_finger(self, finger_id: int) -> Dict[str, Any]:
        """Delete a stored fingerprint.
        
        Args:
            finger_id (int): ID of the fingerprint to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            response = requests.post(
                f"{self.base_url}/delete",
                json={"finger_id": finger_id},
                timeout=5
            )
            return response.json()
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}

    def get_template_count(self) -> int:
        """Get the number of stored fingerprint templates.
        
        Returns:
            Number of stored templates, or -1 if failed
        """
        try:
            response = requests.get(f"{self.base_url}/template-count", timeout=5)
            data = response.json()
            return data.get("count", -1)
        except requests.RequestException:
            return -1

    def start_enrollment(self) -> bool:
        """Start the enrollment process.
        
        Returns:
            bool: True if enrollment process started successfully
        """
        try:
            response = requests.post(
                f"{self.base_url}/init",
                json={"command": "start_enrollment"},
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_enrollment_status(self) -> Dict[str, Any]:
        """Get the current status of an enrollment in progress.
        
        Returns:
            Dict containing:
            - status: 'waiting', 'in_progress', 'complete', or 'error'
            - progress: percentage complete (0-100)
            - message: status message
            - template_data: fingerprint template data (if status is 'complete')
        """
        try:
            response = requests.get(
                f"{self.base_url}/enrollment-status",
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'status': 'error',
                    'progress': 0,
                    'message': 'Failed to get enrollment status'
                }
        except requests.RequestException as e:
            return {
                'status': 'error',
                'progress': 0,
                'message': str(e)
            }

    def get_next_fingerprint_id(self) -> Dict[str, Any]:
        """Get the next available fingerprint ID from the ESP32.
        
        Returns:
            Dict containing:
            - success: bool indicating if the operation was successful
            - nextId: int representing the next available ID (if success is True)
            - message: str containing any error message (if success is False)
        """
        try:
            response = requests.get(
                f"{self.base_url}/enrollment/start",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return {
                        'success': True,
                        'nextId': data.get('nextId')
                    }
                return {
                    'success': False,
                    'message': data.get('message', 'Failed to get next ID')
                }
            return {
                'success': False,
                'message': f'HTTP error {response.status_code}'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'message': str(e)
            }