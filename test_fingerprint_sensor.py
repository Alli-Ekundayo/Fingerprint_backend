import unittest
from unittest.mock import patch, MagicMock
from fingerprint_sensor_module import FingerprintSensor

class TestFingerprintSensor(unittest.TestCase):

    @patch('serial.Serial')
    def test_initialization_success(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'OK\n'

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        self.assertTrue(sensor.initialized)

    @patch('serial.Serial')
    def test_initialization_failure(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.return_value = b'ERROR\n'

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        self.assertFalse(sensor.initialized)

    @patch('serial.Serial')
    def test_start_enrollment_success(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.side_effect = [b'OK\n', b'ENROLLMENT_STARTED\n']

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        result = sensor.start_enrollment()
        self.assertTrue(result)
        self.assertTrue(sensor.enrolling)

    @patch('serial.Serial')
    def test_start_enrollment_failure(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.side_effect = [b'OK\n', b'ERROR\n']

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        result = sensor.start_enrollment()
        self.assertFalse(result)
        self.assertFalse(sensor.enrolling)

    @patch('serial.Serial')
    def test_verify_fingerprint_success(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.side_effect = [b'OK\n', b'{"status": "success", "message": "Fingerprint verified"}\n']

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        result = sensor.verify_fingerprint()
        self.assertEqual(result['status'], 'success')

    @patch('serial.Serial')
    def test_verify_fingerprint_failure(self, mock_serial):
        # Mock the serial connection
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        mock_serial_instance.readline.side_effect = [b'OK\n', b'{"status": "error", "message": "Fingerprint not recognized"}\n']

        sensor = FingerprintSensor(port='COM3', baudrate=115200)
        result = sensor.verify_fingerprint()
        self.assertEqual(result['status'], 'error')

if __name__ == '__main__':
    unittest.main()