/*
 * IoT-based Fingerprint Attendance System
 * 
 * This sketch implements a fingerprint-based attendance system that
 * communicates with a Flask backend server via WiFi.
 * 
 * Hardware:
 * - ESP8266/ESP32
 * - Adafruit Fingerprint Sensor (FPM10A)
 * - 16x2 LCD with I2C adapter
 * - Push buttons for user interaction
 * - LED indicators
 * 
 * Libraries Required:
 * - ESP8266WiFi (for ESP8266) or WiFi (for ESP32)
 * - Adafruit_Fingerprint
 * - LiquidCrystal_I2C
 * - ArduinoJson
 * - ESP8266HTTPClient or HTTPClient
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_Fingerprint.h>
#include <ArduinoJson.h>
#include <SoftwareSerial.h>

// WiFi credentials
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Server API endpoints
const char* SERVER_URL = "http://your-server-url.com";
const char* COURSES_ENDPOINT = "/api/courses";
const char* VERIFY_FINGERPRINT_ENDPOINT = "/api/verify-fingerprint";
const char* ATTENDANCE_ENDPOINT = "/api/attendance";

// Hardware pins
#define FINGERPRINT_RX 2  // Connect to TX on fingerprint sensor
#define FINGERPRINT_TX 3  // Connect to RX on fingerprint sensor
#define SELECT_BTN 5
#define UP_BTN 6
#define DOWN_BTN 7
#define BACK_BTN 8
#define GREEN_LED 9
#define RED_LED 10
#define YELLOW_LED 11

// System state definitions
enum SystemState {
  STATE_INIT,
  STATE_CONNECT_WIFI,
  STATE_FETCH_COURSES,
  STATE_SELECT_COURSE,
  STATE_WAIT_FINGERPRINT,
  STATE_SCANNING_FINGERPRINT,
  STATE_VERIFY_FINGERPRINT,
  STATE_RECORD_ATTENDANCE,
  STATE_SHOW_RESULT,
  STATE_ERROR
};

// Global variables
SystemState currentState = STATE_INIT;
LiquidCrystal_I2C lcd(0x27, 16, 2);  // I2C address 0x27, 16 columns and 2 rows
SoftwareSerial fingerprintSerial(FINGERPRINT_RX, FINGERPRINT_TX);
Adafruit_Fingerprint fingerprintSensor = Adafruit_Fingerprint(&fingerprintSerial);

// Course data
struct Course {
  int id;
  String code;
  String title;
};

Course courses[10];  // Store up to 10 courses
int courseCount = 0;
int selectedCourseIndex = 0;

// Student data
struct Student {
  int id;
  String studentId;
  String name;
};

Student currentStudent;

// Attendance data for offline storage
struct AttendanceRecord {
  int studentId;
  int courseId;
  String status;
  String timestamp;
  bool synced;
};

AttendanceRecord offlineRecords[50];  // Store up to 50 offline records
int offlineRecordCount = 0;

// Function prototypes
bool connectToWiFi();
bool fetchCourses();
void showCourseSelection();
void handleButtonPress();
bool scanFingerprint();
bool verifyFingerprint(int fingerprintId);
bool recordAttendance(int studentId, int courseId);
void syncOfflineRecords();
void showMessage(String line1, String line2 = "");
void blinkLED(int pin, int times, int delayMs);

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("\nIoT Fingerprint Attendance System");
  
  // Initialize hardware pins
  pinMode(SELECT_BTN, INPUT_PULLUP);
  pinMode(UP_BTN, INPUT_PULLUP);
  pinMode(DOWN_BTN, INPUT_PULLUP);
  pinMode(BACK_BTN, INPUT_PULLUP);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(YELLOW_LED, OUTPUT);
  
  // Turn on all LEDs briefly for testing
  digitalWrite(GREEN_LED, HIGH);
  digitalWrite(RED_LED, HIGH);
  digitalWrite(YELLOW_LED, HIGH);
  delay(500);
  digitalWrite(GREEN_LED, LOW);
  digitalWrite(RED_LED, LOW);
  digitalWrite(YELLOW_LED, LOW);
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  showMessage("Fingerprint", "Attendance System");
  delay(2000);
  
  // Initialize fingerprint sensor
  fingerprintSerial.begin(57600);
  
  if (fingerprintSensor.verifyPassword()) {
    showMessage("Fingerprint sensor", "detected");
    Serial.println("Fingerprint sensor found");
  } else {
    showMessage("Fingerprint sensor", "not found!");
    Serial.println("Fingerprint sensor not found");
    currentState = STATE_ERROR;
    return;
  }
  
  // Start with connecting to WiFi
  currentState = STATE_CONNECT_WIFI;
}

void loop() {
  // State machine for the system
  switch (currentState) {
    case STATE_INIT:
      // Initialize the system
      showMessage("Initializing...");
      delay(1000);
      currentState = STATE_CONNECT_WIFI;
      break;
      
    case STATE_CONNECT_WIFI:
      // Connect to WiFi network
      showMessage("Connecting to", WIFI_SSID);
      
      if (connectToWiFi()) {
        showMessage("Connected!", "Fetching courses...");
        currentState = STATE_FETCH_COURSES;
      } else {
        showMessage("WiFi connection", "failed!");
        digitalWrite(RED_LED, HIGH);
        delay(3000);
        digitalWrite(RED_LED, LOW);
        // Retry after a delay
        delay(5000);
      }
      break;
      
    case STATE_FETCH_COURSES:
      // Fetch available courses
      if (fetchCourses()) {
        showMessage("Courses loaded", String(courseCount) + " available");
        delay(1000);
        currentState = STATE_SELECT_COURSE;
      } else {
        showMessage("Failed to fetch", "courses!");
        digitalWrite(RED_LED, HIGH);
        delay(3000);
        digitalWrite(RED_LED, LOW);
        // Retry after a delay
        delay(5000);
      }
      break;
      
    case STATE_SELECT_COURSE:
      // Show course selection interface
      showCourseSelection();
      // Handle button presses for selection
      handleButtonPress();
      break;
      
    case STATE_WAIT_FINGERPRINT:
      // Wait for finger placement
      showMessage("Place finger on", "the sensor");
      digitalWrite(YELLOW_LED, HIGH);
      
      // Check if finger is placed
      if (fingerprintSensor.getImage() == FINGERPRINT_OK) {
        digitalWrite(YELLOW_LED, LOW);
        showMessage("Finger detected", "Scanning...");
        currentState = STATE_SCANNING_FINGERPRINT;
      }
      break;
      
    case STATE_SCANNING_FINGERPRINT:
      // Scan the fingerprint
      if (scanFingerprint()) {
        showMessage("Scan successful", "Verifying...");
        currentState = STATE_VERIFY_FINGERPRINT;
      } else {
        showMessage("Scan failed!", "Try again");
        digitalWrite(RED_LED, HIGH);
        delay(1000);
        digitalWrite(RED_LED, LOW);
        currentState = STATE_WAIT_FINGERPRINT;
      }
      break;
      
    case STATE_VERIFY_FINGERPRINT:
      // Verify the fingerprint against the database
      if (verifyFingerprint(1)) {  // Use fingerprint ID 1 for testing
        showMessage("Verified: " + currentStudent.name, "Recording...");
        currentState = STATE_RECORD_ATTENDANCE;
      } else {
        showMessage("Verification", "failed!");
        digitalWrite(RED_LED, HIGH);
        delay(2000);
        digitalWrite(RED_LED, LOW);
        currentState = STATE_WAIT_FINGERPRINT;
      }
      break;
      
    case STATE_RECORD_ATTENDANCE:
      // Record attendance for the verified student
      if (recordAttendance(currentStudent.id, courses[selectedCourseIndex].id)) {
        showMessage("Attendance", "recorded!");
        digitalWrite(GREEN_LED, HIGH);
        delay(2000);
        digitalWrite(GREEN_LED, LOW);
      } else {
        // Store locally if server is unavailable
        showMessage("Stored locally", "Will sync later");
        digitalWrite(YELLOW_LED, HIGH);
        delay(2000);
        digitalWrite(YELLOW_LED, LOW);
        
        // Add to offline storage
        if (offlineRecordCount < 50) {
          offlineRecords[offlineRecordCount].studentId = currentStudent.id;
          offlineRecords[offlineRecordCount].courseId = courses[selectedCourseIndex].id;
          offlineRecords[offlineRecordCount].status = "present";
          // TODO: Get real timestamp
          offlineRecords[offlineRecordCount].timestamp = "2025-04-05T12:00:00";
          offlineRecords[offlineRecordCount].synced = false;
          offlineRecordCount++;
        }
      }
      currentState = STATE_SHOW_RESULT;
      break;
      
    case STATE_SHOW_RESULT:
      // Show result briefly, then go back to waiting for fingerprint
      delay(2000);
      showMessage(courses[selectedCourseIndex].code, "Scan next finger");
      currentState = STATE_WAIT_FINGERPRINT;
      
      // Try to sync offline records periodically
      if (offlineRecordCount > 0 && WiFi.status() == WL_CONNECTED) {
        syncOfflineRecords();
      }
      break;
      
    case STATE_ERROR:
      // Error state - blink red LED
      showMessage("System Error", "Check connections");
      blinkLED(RED_LED, 3, 300);
      delay(2000);
      break;
  }
}

// Connect to WiFi network
bool connectToWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  // Wait for connection with timeout
  int timeout = 20;  // 10 seconds
  while (WiFi.status() != WL_CONNECTED && timeout > 0) {
    delay(500);
    Serial.print(".");
    timeout--;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    return true;
  } else {
    Serial.println("\nWiFi connection failed");
    return false;
  }
}

// Fetch available courses from the server
bool fetchCourses() {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + String(COURSES_ENDPOINT);
  
  http.begin(url);
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Courses API response:");
    Serial.println(payload);
    
    // Parse JSON response
    DynamicJsonDocument doc(2048);
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
      Serial.print("JSON parsing failed: ");
      Serial.println(error.c_str());
      http.end();
      return false;
    }
    
    // Extract courses
    JsonArray coursesArray = doc["courses"];
    courseCount = min((int)coursesArray.size(), 10);
    
    for (int i = 0; i < courseCount; i++) {
      courses[i].id = coursesArray[i]["id"];
      courses[i].code = coursesArray[i]["code"].as<String>();
      courses[i].title = coursesArray[i]["title"].as<String>();
    }
    
    http.end();
    return true;
  } else {
    Serial.print("HTTP GET failed, error: ");
    Serial.println(httpCode);
    http.end();
    return false;
  }
}

// Display course selection interface
void showCourseSelection() {
  if (courseCount == 0) {
    showMessage("No courses", "available");
    return;
  }
  
  String line1 = String(selectedCourseIndex + 1) + "/" + String(courseCount) + " " + courses[selectedCourseIndex].code;
  String line2 = courses[selectedCourseIndex].title;
  
  // Truncate if too long
  if (line2.length() > 16) {
    line2 = line2.substring(0, 13) + "...";
  }
  
  showMessage(line1, line2);
}

// Handle button presses for course selection
void handleButtonPress() {
  // Check SELECT button
  if (digitalRead(SELECT_BTN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(SELECT_BTN) == LOW) {
      // Course selected, wait for fingerprint
      showMessage("Selected: " + courses[selectedCourseIndex].code, "Place finger");
      currentState = STATE_WAIT_FINGERPRINT;
      delay(500);  // Prevent multiple presses
      while (digitalRead(SELECT_BTN) == LOW) {
        // Wait for button release
        delay(10);
      }
    }
  }
  
  // Check UP button
  if (digitalRead(UP_BTN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(UP_BTN) == LOW) {
      // Move to previous course
      if (selectedCourseIndex > 0) {
        selectedCourseIndex--;
      } else {
        selectedCourseIndex = courseCount - 1;  // Wrap around
      }
      showCourseSelection();
      delay(300);  // Prevent multiple presses
    }
  }
  
  // Check DOWN button
  if (digitalRead(DOWN_BTN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(DOWN_BTN) == LOW) {
      // Move to next course
      selectedCourseIndex = (selectedCourseIndex + 1) % courseCount;
      showCourseSelection();
      delay(300);  // Prevent multiple presses
    }
  }
  
  // Check BACK button
  if (digitalRead(BACK_BTN) == LOW) {
    delay(50);  // Debounce
    if (digitalRead(BACK_BTN) == LOW) {
      // Go back to course fetching
      currentState = STATE_FETCH_COURSES;
      delay(500);  // Prevent multiple presses
    }
  }
}

// Scan fingerprint and extract features
bool scanFingerprint() {
  uint8_t p = fingerprintSensor.image2Tz();
  if (p != FINGERPRINT_OK) {
    Serial.print("Image conversion failed, status: ");
    Serial.println(p);
    return false;
  }
  
  return true;
}

// Verify fingerprint with the server
bool verifyFingerprint(int fingerprintId) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + String(VERIFY_FINGERPRINT_ENDPOINT);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(256);
  doc["fingerprint_id"] = fingerprintId;
  
  String requestBody;
  serializeJson(doc, requestBody);
  
  int httpCode = http.POST(requestBody);
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Verify Fingerprint API response:");
    Serial.println(payload);
    
    // Parse JSON response
    DynamicJsonDocument responseDoc(1024);
    DeserializationError error = deserializeJson(responseDoc, payload);
    
    if (error) {
      Serial.print("JSON parsing failed: ");
      Serial.println(error.c_str());
      http.end();
      return false;
    }
    
    // Check if verification was successful
    bool success = responseDoc["success"];
    
    if (success) {
      // Extract student information
      JsonObject student = responseDoc["student"];
      currentStudent.id = student["id"];
      currentStudent.studentId = student["student_id"].as<String>();
      currentStudent.name = student["name"].as<String>();
      
      http.end();
      return true;
    } else {
      http.end();
      return false;
    }
  } else {
    Serial.print("HTTP POST failed, error: ");
    Serial.println(httpCode);
    http.end();
    return false;
  }
}

// Record attendance for a student
bool recordAttendance(int studentId, int courseId) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }
  
  HTTPClient http;
  String url = String(SERVER_URL) + String(ATTENDANCE_ENDPOINT);
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(256);
  doc["student_id"] = studentId;
  doc["course_id"] = courseId;
  doc["status"] = "present";
  // In a real implementation, you'd use NTP to get accurate time
  doc["timestamp"] = "2025-04-05T12:00:00";
  
  String requestBody;
  serializeJson(doc, requestBody);
  
  int httpCode = http.POST(requestBody);
  
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Record Attendance API response:");
    Serial.println(payload);
    
    // Parse JSON response
    DynamicJsonDocument responseDoc(256);
    DeserializationError error = deserializeJson(responseDoc, payload);
    
    if (error) {
      Serial.print("JSON parsing failed: ");
      Serial.println(error.c_str());
      http.end();
      return false;
    }
    
    // Check if recording was successful
    bool success = responseDoc["success"];
    
    http.end();
    return success;
  } else {
    Serial.print("HTTP POST failed, error: ");
    Serial.println(httpCode);
    http.end();
    return false;
  }
}

// Sync offline attendance records
void syncOfflineRecords() {
  if (WiFi.status() != WL_CONNECTED || offlineRecordCount == 0) {
    return;
  }
  
  showMessage("Syncing offline", "records...");
  digitalWrite(YELLOW_LED, HIGH);
  
  int syncCount = 0;
  
  for (int i = 0; i < offlineRecordCount; i++) {
    if (!offlineRecords[i].synced) {
      // Try to sync this record
      if (recordAttendance(offlineRecords[i].studentId, offlineRecords[i].courseId)) {
        offlineRecords[i].synced = true;
        syncCount++;
      }
    }
  }
  
  digitalWrite(YELLOW_LED, LOW);
  
  if (syncCount > 0) {
    showMessage("Sync complete", String(syncCount) + " records");
    digitalWrite(GREEN_LED, HIGH);
    delay(1000);
    digitalWrite(GREEN_LED, LOW);
  }
}

// Display a message on the LCD
void showMessage(String line1, String line2) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  
  if (line2.length() > 0) {
    lcd.setCursor(0, 1);
    lcd.print(line2);
  }
}

// Blink an LED
void blinkLED(int pin, int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(delayMs);
    digitalWrite(pin, LOW);
    delay(delayMs);
  }
}
