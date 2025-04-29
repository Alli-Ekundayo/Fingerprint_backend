import logging
import time
import random
import json
import serial  # For serial communication with ESP32
from datetime import datetime

logger = logging.getLogger(__name__)

class FingerprintSensor:
    """
    Class to interface with fingerprint sensor hardware via ESP32.
    """

    def __init__(self, port=None, baudrate=115200):
        """Initialize the fingerprint sensor interface"""
        self.initialized = False
        self.enrolling = False
        self.enrollment_stage = 0
        self.port = port
        self.baudrate = baudrate
        self._connect()

    def _connect(self):
        """Establish connection to the ESP32"""
        # Try to find available ports if none specified
        if self.port is None:
            try:
                import serial.tools.list_ports
                available_ports = list(serial.tools.list_ports.comports())
                if available_ports:
                    # Try to find a port that might be the ESP32
                    esp_port = next((p.device for p in available_ports if any(x in p.description.lower() for x in ['cp210x', 'uart', 'usb serial'])), None)
                    self.port = esp_port or available_ports[0].device
                    logger.info(f"Auto-detected port: {self.port}")
                else:
                    self.port = 'COM3'  # Fallback to default
                    logger.warning("No ports found, falling back to default COM3")
            except Exception as e:
                logger.error(f"Error detecting ports: {e}")
                self.port = 'COM3'  # Fallback to default

        # Serial connection to ESP32
        try:
            if hasattr(self, 'serial_connection') and self.serial_connection:
                self.close()
            
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            logger.info(f"Attempting to connect to ESP32 on port {self.port}")
            self._initialize()
        except serial.serialutil.SerialException as e:
            logger.error(f"Failed to connect to ESP32 on port {self.port}: {e}")
            logger.info("Please check:\n1. ESP32 is connected via USB\n2. Correct drivers are installed\n3. Correct COM port is being used")
            self.serial_connection = None

    def _initialize(self):
        """Initialize the fingerprint sensor hardware via ESP32"""
        if not self.serial_connection:
            logger.error("Serial connection not established")
            return

        logger.info("Initializing fingerprint sensor via ESP32...")
        self.serial_connection.write(b'INIT\n')  # Send initialization command to ESP32
        response = self.serial_connection.readline().decode().strip()

        if response == 'OK':
            self.initialized = True
            logger.info("Fingerprint sensor initialized successfully")
        else:
            logger.error(f"Initialization failed: {response}")

    def start_enrollment(self):
        """Start the fingerprint enrollment process"""
        if not self.initialized:
            logger.error("Cannot start enrollment: Sensor not initialized")
            return False

        logger.info("Starting fingerprint enrollment process")
        self.serial_connection.write(b'START_ENROLLMENT\n')  # Command to start enrollment
        response = self.serial_connection.readline().decode().strip()

        if response == 'ENROLLMENT_STARTED':
            self.enrolling = True
            self.enrollment_stage = 1
            return True
        else:
            logger.error(f"Failed to start enrollment: {response}")
            return False

    def get_enrollment_status(self):
        """
        Get the current status of enrollment from ESP32
        """
        if not self.enrolling:
            return {
                'status': 'error',
                'message': 'No enrollment in progress',
                'progress': 0
            }

        self.serial_connection.write(b'GET_ENROLLMENT_STATUS\n')  # Request status
        response = self.serial_connection.readline().decode().strip()

        try:
            status_data = json.loads(response)  # Parse JSON response from ESP32
            return status_data
        except json.JSONDecodeError:
            logger.error(f"Invalid response from ESP32: {response}")
            return {
                'status': 'error',
                'message': 'Invalid response from sensor',
                'progress': 0
            }

    def verify_fingerprint(self):
        """
        Verify a fingerprint against stored templates via ESP32
        """
        if not self.initialized:
            logger.error("Cannot verify fingerprint: Sensor not initialized")
            return {
                'status': 'error',
                'message': 'Sensor not initialized'
            }

        self.serial_connection.write(b'VERIFY_FINGERPRINT\n')  # Command to verify fingerprint
        response = self.serial_connection.readline().decode().strip()

        try:
            verification_data = json.loads(response)  # Parse JSON response from ESP32
            return verification_data
        except json.JSONDecodeError:
            logger.error(f"Invalid response from ESP32: {response}")
            return {
                'status': 'error',
                'message': 'Invalid response from sensor'
            }

    def cancel_operation(self):
        """Cancel any ongoing operation via ESP32"""
        if not self.serial_connection:
            logger.error("Serial connection not established")
            return False

        self.serial_connection.write(b'CANCEL_OPERATION\n')  # Command to cancel operation
        response = self.serial_connection.readline().decode().strip()

        if response == 'OPERATION_CANCELLED':
            self.enrolling = False
            self.enrollment_stage = 0
            logger.info("Fingerprint operation cancelled")
            return True
        else:
            logger.error(f"Failed to cancel operation: {response}")
            return False

    def get_status(self):
        """Get the current status of the sensor via ESP32"""
        if not self.serial_connection:
            return {
                'status': 'error',
                'message': 'Serial connection not established'
            }

        self.serial_connection.write(b'GET_STATUS\n')  # Request sensor status
        response = self.serial_connection.readline().decode().strip()

        try:
            status_data = json.loads(response)  # Parse JSON response from ESP32
            return status_data
        except json.JSONDecodeError:
            logger.error(f"Invalid response from ESP32: {response}")
            return {
                'status': 'error',
                'message': 'Invalid response from sensor'
            }

    def close(self):
        """Properly close the serial connection"""
        if hasattr(self, 'serial_connection') and self.serial_connection:
            try:
                self.serial_connection.close()
                logger.info(f"Closed connection to port {self.port}")
            except Exception as e:
                logger.error(f"Error closing port {self.port}: {e}")
            self.serial_connection = None
            self.initialized = False

    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close()
