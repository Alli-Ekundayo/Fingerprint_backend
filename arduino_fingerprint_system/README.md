# Arduino Fingerprint Attendance System

This directory contains the Arduino implementation for the IoT-based fingerprint attendance system. The Arduino device acts as a client that communicates with the Flask backend server through API endpoints.

## Hardware Requirements

- Arduino Mega 2560 or ESP32/ESP8266 (for WiFi capability)
- Adafruit Fingerprint Sensor (FPM10A)
- 16x2 LCD Display
- Push buttons for interaction
- LED indicators
- Power supply

## Circuit Diagram

See the `circuit_diagram.txt` file for a detailed circuit connection guide.

## Software Components

1. **Fingerprint sensor interface** - Manages fingerprint enrollment and verification.
2. **LCD interface** - Displays system status and user instructions.
3. **WiFi connection manager** - Handles network connectivity.
4. **API client** - Communicates with the Flask backend server.
5. **State machine** - Controls the overall system flow.

## Setup Instructions

1. Connect the hardware components according to the circuit diagram.
2. Update the WiFi credentials and server URL in the Arduino code.
3. Upload the code to your Arduino device.
4. Test the connection using the provided `api_test.py` script.

## API Endpoints Used

- **GET /api/courses** - Retrieves available courses.
- **POST /api/verify-fingerprint** - Verifies a fingerprint against the database.
- **POST /api/attendance** - Records attendance for a verified student.

## Testing the API

You can use the `api_test.py` script to test the API endpoints:

```bash
# Make sure the script is executable
chmod +x api_test.py

# Run the script
./api_test.py
```

## How It Works

1. **Initialization**:
   - Connect to WiFi network
   - Display welcome message on LCD
   - Initialize the fingerprint sensor

2. **Course Selection**:
   - Device fetches available courses from the server
   - User selects a course using buttons

3. **Fingerprint Scanning**:
   - User places finger on the sensor
   - Device captures the fingerprint image
   - Fingerprint is sent to server for verification

4. **Attendance Recording**:
   - If fingerprint is verified, the attendance is recorded
   - LCD displays confirmation message
   - LED indicates success/failure

5. **Offline Mode**:
   - If network is unavailable, attendance is stored locally
   - Device automatically syncs when connection is restored

## Troubleshooting

- **Fingerprint Sensor Issues**: Ensure clean finger placement and proper sensor connection.
- **WiFi Connectivity**: Check WiFi credentials and signal strength.
- **API Communication**: Verify server URL and connectivity.
