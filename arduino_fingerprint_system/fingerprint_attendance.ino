#include <WiFi.h>
#include <WiFiMulti.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Adafruit_Fingerprint.h>
#include <time.h>
#include <SPIFFS.h>
#include <WebServer.h>

// Pin Definitions
#define FINGERPRINT_RX 16
#define FINGERPRINT_TX 17
#define LED_GREEN 25
#define LED_YELLOW 26
#define LED_RED 27
#define BTN_SELECT 12
#define BTN_UP 13
#define BTN_DOWN 14
#define BTN_BACK 15

// Configuration
#define LCD_COLS 16
#define LCD_ROWS 2
#define LCD_ADDRESS 0x27
#define SERVER_URL "http://192.168.43.164:5000"
#define MAX_OFFLINE_RECORDS 50
#define NTP_SERVER "pool.ntp.org"

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Initialize the web server on port 80
WebServer server(80);

// State Machine States
enum SystemState {
  INIT,
  CONNECT_WIFI,
  FETCH_COURSES,
  SELECT_COURSE,
  WAIT_FINGERPRINT,
  SCAN_FINGERPRINT,
  VERIFY_FINGERPRINT,
  RECORD_ATTENDANCE,
  SHOW_RESULT,
  SYNC_OFFLINE
};

// Global Variables
SystemState currentState = INIT;
WiFiMulti wifiMulti;
LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLS, LCD_ROWS);
// Use HardwareSerial2 for fingerprint sensor
HardwareSerial fingerprintSerial(2);  // UART2 on ESP32
Adafruit_Fingerprint fingerSensor = Adafruit_Fingerprint(&fingerprintSerial);

// Course and attendance related variables
struct Course {
  String id;
  String title;
  String code;
};

struct AttendanceRecord {
  String courseId;
  uint32_t fingerprintId;
  time_t timestamp;
  bool synced;
};

Course courses[10];  // Maximum 10 courses support
int courseCount = 0;
int selectedCourseIndex = 0;
AttendanceRecord offlineBuffer[MAX_OFFLINE_RECORDS];
int offlineRecordCount = 0;
uint32_t lastButtonPressTime = 0;
const uint32_t debounceDelay = 200;  // Debounce delay in ms

bool enrollmentInProgress = false;
int enrollmentProgress = 0;
uint8_t lastEnrollmentStatus = FINGERPRINT_NOFINGER;

void setup() {
  // Initialize serial communication
  Serial.begin(115200);
  Serial.println("Fingerprint Attendance System Starting...");

  // Initialize SPIFFS for offline storage
  if (!SPIFFS.begin(true)) {
    Serial.println("Failed to mount SPIFFS");
  }

  // Set pin modes
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);
  pinMode(LED_RED, OUTPUT);
  pinMode(BTN_SELECT, INPUT_PULLUP);
  pinMode(BTN_UP, INPUT_PULLUP);
  pinMode(BTN_DOWN, INPUT_PULLUP);
  pinMode(BTN_BACK, INPUT_PULLUP);

  // Initialize LEDs (all off)
  digitalWrite(LED_GREEN, LOW);
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, LOW);

  // Initialize LCD
  Wire.begin();
  lcd.init();
  lcd.backlight();
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Attendance System");
  lcd.setCursor(0, 1);
  lcd.print("Initializing...");

  // Initialize fingerprint sensor using hardware serial
  fingerprintSerial.begin(57600, SERIAL_8N1, FINGERPRINT_RX, FINGERPRINT_TX);
  
  if (fingerSensor.verifyPassword()) {
    Serial.println("Fingerprint sensor connected!");
  } else {
    Serial.println("Fingerprint sensor not found");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sensor Error!");
    digitalWrite(LED_RED, HIGH);
    delay(2000);
  }

  // Initialize WiFi in station mode
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();  // Disconnect from any previous connections
  delay(100);

  Serial.println("Scanning for WiFi networks...");
  int n = WiFi.scanNetworks();
  if (n == 0) {
    Serial.println("No networks found");
  } else {
    Serial.print(n);
    Serial.println(" networks found");
    for (int i = 0; i < n; ++i) {
      Serial.printf("%d: %s (Signal: %d dBm)\n", i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i));
      delay(10);
    }
  }

  // Configure WiFi networks (make sure these match your network)
  wifiMulti.addAP("HUAWEI P smart 2019", "123456789012");  // Primary network

  // Set WiFi connection timeout
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  
  // Configure NTP
  configTime(0, 0, NTP_SERVER);  // UTC time, no DST offset

  // Load any existing offline records
  loadOfflineRecords();
  
  // Initial state
  currentState = CONNECT_WIFI;

  // Set up HTTP endpoints
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/init", HTTP_POST, handleInit);
  server.on("/enroll", HTTP_POST, handleEnroll);
  server.on("/verify", HTTP_POST, handleVerify);
  server.on("/delete", HTTP_POST, handleDelete);
  server.on("/template-count", HTTP_GET, handleTemplateCount);
  server.on("/start-enrollment", HTTP_POST, handleStartEnrollment);
  server.on("/enrollment-status", HTTP_GET, handleEnrollmentStatus);

  server.begin();
}

/**
 * Handles WiFi connection with timeout and visual feedback
 */
void handleWiFiConnection() {
  static uint32_t connectionStartTime = 0;
  const uint32_t connectionTimeout = 30000;  // 30 seconds
  
  // First entry to this state
  if (connectionStartTime == 0) {
    Serial.println("Connecting to WiFi...");
    connectionStartTime = millis();
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting WiFi");
    digitalWrite(LED_YELLOW, HIGH);
  }
  
  // Check if connected
  if (wifiMulti.run() == WL_CONNECTED) {
    Serial.println("WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Connected");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_GREEN, HIGH);
    delay(1000);
    digitalWrite(LED_GREEN, LOW);
    
    // Sync time with NTP server
    configTime(0, 0, NTP_SERVER);
    
    currentState = FETCH_COURSES;
    connectionStartTime = 0;  // Reset for next time
    return;
  }
  
  // Check for timeout
  if (millis() - connectionStartTime > connectionTimeout) {
    Serial.println("WiFi connection timeout");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed");
    lcd.setCursor(0, 1);
    lcd.print("Using Offline");
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    delay(1000);
    digitalWrite(LED_RED, LOW);
    
    // Skip to course selection with cached data
    if (courseCount > 0) {
      currentState = SELECT_COURSE;
    } else {
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("No cached data");
      lcd.setCursor(0, 1);
      lcd.print("Retrying WiFi...");
      delay(2000);
      // Will retry WiFi connection
    }
    connectionStartTime = 0;  // Reset for next time
  } else {
    // Visual feedback during connection
    lcd.setCursor(0, 1);
    lcd.print("                ");  // Clear second line
    lcd.setCursor(0, 1);
    lcd.print("Trying... ");
    lcd.print((millis() - connectionStartTime) / 1000);
    lcd.print("s");
    delay(200);
  }
}

/**
 * Fetches course list from server via HTTP
 */
bool fetchCourseList() {
  digitalWrite(LED_YELLOW, HIGH);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Fetching courses");
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, cannot fetch courses");
    handleFetchError("No WiFi");
    
    // Try to load cached course data
    if (loadCourseData()) {
      currentState = SELECT_COURSE;
    }
    return true;
  }

  HTTPClient http;
  String url = String(SERVER_URL) + "/api/courses";
  
  Serial.print("Connecting to: ");
  Serial.println(url);
  
  http.begin(url);
  http.setTimeout(15000); // 15 second timeout
  int httpCode = http.GET();

  // httpCode will be negative on error
  if (httpCode > 0) {
    Serial.print("HTTP response code: ");
    Serial.println(httpCode);
    
    // HTTP 200 OK
    if (httpCode == HTTP_CODE_OK) {
      String payload = http.getString();
      Serial.println("Courses API response received:");
      Serial.println(payload);
      
      // Parse JSON response
      DynamicJsonDocument doc(2048);
      DeserializationError error = deserializeJson(doc, payload);
      
      if (error) {
        Serial.print("JSON parsing failed: ");
        Serial.println(error.c_str());
        http.end();
        handleFetchError("JSON Error");
        return false;
      }
      
      // Check if response contains courses array
      if (!doc.containsKey("courses")) {
        Serial.println("Error: Response missing 'courses' array");
        http.end();
        handleFetchError("Invalid Data");
        return false;
      }
      
      // Extract courses
      JsonArray coursesArray = doc["courses"];
      courseCount = min((int)coursesArray.size(), 10);
      
      Serial.print("Found ");
      Serial.print(courseCount);
      Serial.println(" courses");
      
      for (int i = 0; i < courseCount; i++) {
        courses[i].id = coursesArray[i]["id"].as<String>();
        courses[i].code = coursesArray[i]["code"].as<String>();
        courses[i].title = coursesArray[i]["title"].as<String>();
        
        Serial.print("Course ");
        Serial.print(i + 1);
        Serial.print(": ");
        Serial.print(courses[i].code);
        Serial.print(" - ");
        Serial.println(courses[i].title);
      }
      
      // Save courses for offline use
      saveCourseData();
      
      // Turn off yellow LED and show success briefly
      digitalWrite(LED_YELLOW, LOW);
      digitalWrite(LED_GREEN, HIGH);
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Found ");
      lcd.print(courseCount);
      lcd.print(" courses");
      delay(1000);
      digitalWrite(LED_GREEN, LOW);
      
      // Transition to course selection
      currentState = SELECT_COURSE;
      
      http.end();
      return true;
    } else {
      // Other HTTP error codes
      Serial.print("HTTP GET returned error code: ");
      Serial.println(httpCode);
      String payload = http.getString();
      Serial.print("Server response: ");
      Serial.println(payload);
      handleFetchError("HTTP " + String(httpCode));
    }
  } else {
    Serial.print("HTTP connection failed with error: ");
    Serial.println(http.errorToString(httpCode));
    handleFetchError("Conn Failed");
  }
  
  http.end();
  return false;
}

/**
 * Handles error during course fetch
 */
void handleFetchError(String errorMsg) {
  digitalWrite(LED_YELLOW, LOW);
  digitalWrite(LED_RED, HIGH);
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Fetch Error!");
  lcd.setCursor(0, 1);
  lcd.print(errorMsg);
  
  delay(2000);
  digitalWrite(LED_RED, LOW);
}

/**
 * Handles course selection interface on LCD
 */
void handleCourseSelection() {
  static bool firstEntry = true;
  
  if (firstEntry) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Select Course:");
    displayCourse();
    firstEntry = false;
  }
  
  // Button handling is in the handleButtonInputs() function
  // This function mainly handles display updates
  
  if (digitalRead(BTN_SELECT) == LOW && millis() - lastButtonPressTime > debounceDelay) {
    lastButtonPressTime = millis();
    firstEntry = true;  // Reset for next time
    currentState = WAIT_FINGERPRINT;
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Selected:");
    lcd.setCursor(0, 1);
    lcd.print(courses[selectedCourseIndex].title);
    delay(1000);
  }
}

/**
 * Displays current course in the selection
 */
void displayCourse() {
  lcd.setCursor(0, 1);
  lcd.print("                ");  // Clear line
  lcd.setCursor(0, 1);
  
  String courseName = courses[selectedCourseIndex].title;
  if (courseName.length() > 16) {
    courseName = courseName.substring(0, 13) + "...";
  }
  
  lcd.print(courseName);
}

/**
 * Wait for a finger to be placed on the sensor
 */
void waitForFingerprint() {
  static bool firstEntry = true;
  static unsigned long animationTimer = 0;
  static int animationState = 0;
  
  if (firstEntry) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Place finger");
    lcd.setCursor(0, 1);
    lcd.print("on sensor");
    digitalWrite(LED_YELLOW, HIGH);
    firstEntry = false;
    animationTimer = millis();
  }
  
  // Simple animation for visual feedback
  if (millis() - animationTimer > 500) {
    animationTimer = millis();
    lcd.setCursor(15, 0);
    lcd.print(animationState % 2 == 0 ? ">" : " ");
    animationState++;
  }
  
  // Check if finger is present
  uint8_t p = fingerSensor.getImage();
  if (p == FINGERPRINT_OK) {
    Serial.println("Image taken");
    digitalWrite(LED_YELLOW, LOW);
    firstEntry = true;  // Reset for next time
    currentState = SCAN_FINGERPRINT;
  } else if (digitalRead(BTN_BACK) == LOW && millis() - lastButtonPressTime > debounceDelay) {
    lastButtonPressTime = millis();
    digitalWrite(LED_YELLOW, LOW);
    firstEntry = true;  // Reset for next time
    currentState = SELECT_COURSE;
  }
}

/**
 * Process fingerprint scan and convert to template
 */
void scanFingerprint() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Processing...");
  digitalWrite(LED_YELLOW, HIGH);
  
  // Convert fingerprint image to characteristics
  uint8_t p = fingerSensor.image2Tz();
  if (p == FINGERPRINT_OK) {
    Serial.println("Image converted");
    currentState = VERIFY_FINGERPRINT;
  } else {
    Serial.print("Image conversion error: ");
    Serial.println(p);
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Scan error!");
    lcd.setCursor(0, 1);
    lcd.print("Try again");
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    delay(2000);
    digitalWrite(LED_RED, LOW);
    
    currentState = WAIT_FINGERPRINT;
  }
}

/**
 * Verify fingerprint against stored templates
 */
void verifyFingerprint() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Verifying...");
  
  uint8_t p = fingerSensor.fingerFastSearch();
  
  if (p == FINGERPRINT_OK) {
    // Found a match
    uint32_t fingerprintId = fingerSensor.fingerID;
    uint16_t confidence = fingerSensor.confidence;
    
    Serial.print("Found ID #"); Serial.print(fingerprintId);
    Serial.print(" with confidence of "); Serial.println(confidence);
    
    // If online, verify with server
    if (WiFi.status() == WL_CONNECTED) {
      verifyWithServer(fingerprintId);
    } else {
      // Skip online verification if offline
      currentState = RECORD_ATTENDANCE;
    }
  } else {
    // No match found
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("No match found!");
    lcd.setCursor(0, 1);
    lcd.print("Try again");
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    delay(2000);
    digitalWrite(LED_RED, LOW);
    
    currentState = WAIT_FINGERPRINT;
  }
}

/**
 * Verify fingerprint validity with server
 */
void verifyWithServer(uint32_t fingerprintId) {
  HTTPClient http;
  String url = String(SERVER_URL) + "/api/verify-fingerprint";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(256);
  doc["fingerprint_id"] = fingerprintId;
  doc["course_id"] = courses[selectedCourseIndex].id;
  
  String payload;
  serializeJson(doc, payload);
  
  int httpCode = http.POST(payload);
  
  if (httpCode == HTTP_CODE_OK) {
    // Server verification successful
    currentState = RECORD_ATTENDANCE;
  } else {
    // Server verification failed
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Server verify");
    lcd.setCursor(0, 1);
    lcd.print("failed: ");
    lcd.print(httpCode);
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, HIGH);
    delay(2000);
    digitalWrite(LED_RED, LOW);
    
    // Continue to attendance recording anyway, but mark as offline
    currentState = RECORD_ATTENDANCE;
  }
  
  http.end();
}

/**
 * Record attendance locally and attempt to sync with server
 */
void recordAttendance() {
  time_t now;
  time(&now);  // Get current time
  
  uint32_t fingerprintId = fingerSensor.fingerID;
  String courseId = courses[selectedCourseIndex].id;
  
  // Attempt to record attendance online
  bool syncSuccessful = false;
  
  if (WiFi.status() == WL_CONNECTED) {
    syncSuccessful = sendAttendanceToServer(fingerprintId, courseId, now);
  }
  
  if (!syncSuccessful) {
    // Store in offline buffer
    if (offlineRecordCount < MAX_OFFLINE_RECORDS) {
      offlineBuffer[offlineRecordCount].courseId = courseId;
      offlineBuffer[offlineRecordCount].fingerprintId = fingerprintId;
      offlineBuffer[offlineRecordCount].timestamp = now;
      offlineBuffer[offlineRecordCount].synced = false;
      offlineRecordCount++;
      
      // Save to persistent storage
      saveOfflineRecords();
    } else {
      // Buffer full warning
      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Warning:");
      lcd.setCursor(0, 1);
      lcd.print("Buffer full!");
      
      digitalWrite(LED_RED, HIGH);
      delay(1000);
      digitalWrite(LED_RED, LOW);
    }
  }
  
  currentState = SHOW_RESULT;
}

/**
 * Attempt to send attendance record to server
 */
bool sendAttendanceToServer(uint32_t fingerprintId, String courseId, time_t timestamp) {
  HTTPClient http;
  String url = String(SERVER_URL) + "api/attendance";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  // Create JSON payload
  DynamicJsonDocument doc(256);
  doc["fingerprint_id"] = fingerprintId;
  doc["course_id"] = courseId;
  doc["timestamp"] = timestamp;
  
  String payload;
  serializeJson(doc, payload);
  
  int httpCode = http.POST(payload);
  
  http.end();
  return (httpCode == HTTP_CODE_OK);
}

/**
 * Display attendance recording result
 */
void showResult() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Attendance");
  lcd.setCursor(0, 1);
  lcd.print("Recorded!");
  
  digitalWrite(LED_GREEN, HIGH);
  delay(2000);
  digitalWrite(LED_GREEN, LOW);
  
  // Check if we need to sync offline records
  if (WiFi.status() == WL_CONNECTED && offlineRecordCount > 0) {
    currentState = SYNC_OFFLINE;
  } else {
    currentState = SELECT_COURSE;
  }
}

/**
 * Sync offline attendance records with server
 */
void syncOfflineRecords() {
  static int currentSyncIndex = 0;
  
  if (currentSyncIndex == 0) {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Syncing offline");
    lcd.setCursor(0, 1);
    lcd.print("records: 0/");
    lcd.print(offlineRecordCount);
    
    digitalWrite(LED_YELLOW, HIGH);
  }
  
  if (currentSyncIndex < offlineRecordCount) {
    if (!offlineBuffer[currentSyncIndex].synced) {
      bool success = sendAttendanceToServer(
        offlineBuffer[currentSyncIndex].fingerprintId,
        offlineBuffer[currentSyncIndex].courseId,
        offlineBuffer[currentSyncIndex].timestamp
      );
      
      if (success) {
        offlineBuffer[currentSyncIndex].synced = true;
        saveOfflineRecords();
      }
    }
    
    // Update display
    lcd.setCursor(9, 1);
    lcd.print(currentSyncIndex + 1);
    
    currentSyncIndex++;
  } else {
    // Cleanup synced records
    int newCount = 0;
    for (int i = 0; i < offlineRecordCount; i++) {
      if (!offlineBuffer[i].synced) {
        if (i != newCount) {
          offlineBuffer[newCount] = offlineBuffer[i];
        }
        newCount++;
      }
    }
    
    offlineRecordCount = newCount;
    saveOfflineRecords();
    
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sync complete");
    lcd.setCursor(0, 1);
    lcd.print(offlineRecordCount);
    lcd.print(" records left");
    
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_GREEN, HIGH);
    delay(2000);
    digitalWrite(LED_GREEN, LOW);
    
    currentSyncIndex = 0;  // Reset for next time
    currentState = SELECT_COURSE;
  }
}

/**
 * Handle button inputs for navigation
 */
void handleButtonInputs() {
  // UP button - navigate through menus
  if (digitalRead(BTN_UP) == LOW && millis() - lastButtonPressTime > debounceDelay) {
    lastButtonPressTime = millis();
    
    if (currentState == SELECT_COURSE) {
      selectedCourseIndex = (selectedCourseIndex > 0) ? selectedCourseIndex - 1 : courseCount - 1;
      displayCourse();
    }
  }
  
  // DOWN button - navigate through menus
  if (digitalRead(BTN_DOWN) == LOW && millis() - lastButtonPressTime > debounceDelay) {
    lastButtonPressTime = millis();
    
    if (currentState == SELECT_COURSE) {
      selectedCourseIndex = (selectedCourseIndex < courseCount - 1) ? selectedCourseIndex + 1 : 0;
      displayCourse();
    }
  }
  
  // BACK button - return to previous state
  if (digitalRead(BTN_BACK) == LOW && millis() - lastButtonPressTime > debounceDelay) {
    lastButtonPressTime = millis();
    
    switch (currentState) {
      case SELECT_COURSE:
        // If we have offline records and are online, offer to sync
        if (WiFi.status() == WL_CONNECTED && offlineRecordCount > 0) {
          currentState = SYNC_OFFLINE;
        }
        break;
        
      case WAIT_FINGERPRINT:
        currentState = SELECT_COURSE;
        break;
        
      default:
        // Other states don't handle back button
        break;
    }
  }
}

/**
 * Save course data to SPIFFS for offline use
 */
void saveCourseData() {
  File file = SPIFFS.open("/courses.json", "w");
  if (!file) {
    Serial.println("Failed to open courses file for writing");
    return;
  }
  
  DynamicJsonDocument doc(2048);
  
  for (int i = 0; i < courseCount; i++) {
    JsonObject course = doc.createNestedObject();
    course["id"] = courses[i].id;
    course["name"] = courses[i].title;
  }
  
  if (serializeJson(doc, file) == 0) {
    Serial.println("Failed to write courses to file");
  }
  
  file.close();
}

/**
 * Load cached course data from SPIFFS
 */
bool loadCourseData() {
  if (!SPIFFS.exists("/courses.json")) {
    return false;
  }
  
  File file = SPIFFS.open("/courses.json", "r");
  if (!file) {
    Serial.println("Failed to open courses file for reading");
    return false;
  }
  
  DynamicJsonDocument doc(2048);
  DeserializationError error = deserializeJson(doc, file);
  file.close();
  
  if (error) {
    Serial.println("Failed to parse courses file");
    return false;
  }
  
  courseCount = min((int)doc.size(), 10);
  
  for (int i = 0; i < courseCount; i++) {
    courses[i].id = doc[i]["id"].as<String>();
    courses[i].title = doc[i]["title"].as<String>();
  }
  
  Serial.println("Loaded cached course data");
  return true;
}

/**
 * Save offline attendance records to SPIFFS
 */
void saveOfflineRecords() {
  File file = SPIFFS.open("/attendance.json", "w");
  if (!file) {
    Serial.println("Failed to open attendance file for writing");
    return;
  }
  
  DynamicJsonDocument doc(4096);  // Adjust size as needed
  
  for (int i = 0; i < offlineRecordCount; i++) {
    JsonObject record = doc.createNestedObject();
    record["course_id"] = offlineBuffer[i].courseId;
    record["fingerprint_id"] = offlineBuffer[i].fingerprintId;
    record["timestamp"] = offlineBuffer[i].timestamp;
    record["synced"] = offlineBuffer[i].synced;
  }
  
  if (serializeJson(doc, file) == 0) {
    Serial.println("Failed to write attendance to file");
  }
  
  file.close();
}

/**
 * Load offline attendance records from SPIFFS
 */
void loadOfflineRecords() {
  if (!SPIFFS.exists("/attendance.json")) {
    return;
  }
  
  File file = SPIFFS.open("/attendance.json", "r");
  if (!file) {
    Serial.println("Failed to open attendance file for reading");
    return;
  }
  
  DynamicJsonDocument doc(4096);  // Adjust size as needed
  DeserializationError error = deserializeJson(doc, file);
  file.close();
  
  if (error) {
    Serial.println("Failed to parse attendance file");
    return;
  }
  
  offlineRecordCount = min((int)doc.size(), MAX_OFFLINE_RECORDS);
  
  for (int i = 0; i < offlineRecordCount; i++) {
    offlineBuffer[i].courseId = doc[i]["course_id"].as<String>();
    offlineBuffer[i].fingerprintId = doc[i]["fingerprint_id"].as<uint32_t>();
    offlineBuffer[i].timestamp = doc[i]["timestamp"].as<time_t>();
    offlineBuffer[i].synced = doc[i]["synced"].as<bool>();
  }
  
  Serial.println("Loaded offline attendance records");
}

/**
 * Main program loop implementing the state machine
 */
void loop() {
  // Handle button inputs (common across states)
  handleButtonInputs();
  
  // State machine implementation
  switch (currentState) {
    case CONNECT_WIFI:
      handleWiFiConnection();
      break;
      
    case FETCH_COURSES:
      fetchCourseList();
      break;
      
    case SELECT_COURSE:
      handleCourseSelection();
      break;
      
    case WAIT_FINGERPRINT:
      waitForFingerprint();
      break;
      
    case SCAN_FINGERPRINT:
      scanFingerprint();
      break;
      
    case VERIFY_FINGERPRINT:
      verifyFingerprint();
      break;
      
    case RECORD_ATTENDANCE:
      recordAttendance();
      break;
      
    case SHOW_RESULT:
      showResult();
      break;
      
    case SYNC_OFFLINE:
      syncOfflineRecords();
      break;
      
    default:
      // Should never reach here, but just in case
      currentState = INIT;
      break;
  }

  server.handleClient();
}

void handleStatus() {
    if (fingerSensor.verifyPassword()) {
        server.send(200, "application/json", "{\"status\":\"connected\"}");
    } else {
        server.send(500, "application/json", "{\"status\":\"sensor error\"}");
    }
}

void handleInit() {
    if (fingerSensor.verifyPassword()) {
        server.send(200, "application/json", "{\"success\":true}");
    } else {
        server.send(500, "application/json", "{\"success\":false,\"message\":\"Failed to initialize\"}");
    }
}

void handleEnroll() {
    if (!server.hasArg("plain")) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Missing body\"}");
        return;
    }

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, server.arg("plain"));
    
    if (error) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Invalid JSON\"}");
        return;
    }

    int id = doc["finger_id"];
    int result = enrollFinger(id);
    
    if (result == 1) {
        server.send(200, "application/json", "{\"success\":true,\"message\":\"Enrollment successful\"}");
    } else {
        String response = "{\"success\":false,\"message\":\"Enrollment failed: " + String(result) + "\"}";
        server.send(500, "application/json", response);
    }
}

void handleVerify() {
    int result = fingerSensor.getImage();
    if (result != FINGERPRINT_OK) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Failed to capture finger\"}");
        return;
    }

    result = fingerSensor.image2Tz();
    if (result != FINGERPRINT_OK) {
        server.send(500, "application/json", "{\"success\":false,\"message\":\"Failed to convert image\"}");
        return;
    }

    result = fingerSensor.fingerFastSearch();
    if (result == FINGERPRINT_OK) {
        String response = "{\"success\":true,\"finger_id\":" + String(fingerSensor.fingerID) + 
                         ",\"confidence\":" + String(fingerSensor.confidence) + "}";
        server.send(200, "application/json", response);
    } else {
        server.send(404, "application/json", "{\"success\":false,\"message\":\"No match found\"}");
    }
}

void handleDelete() {
    if (!server.hasArg("plain")) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Missing body\"}");
        return;
    }

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, server.arg("plain"));
    
    if (error) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Invalid JSON\"}");
        return;
    }

    int id = doc["finger_id"];
    if (fingerSensor.deleteModel(id) == FINGERPRINT_OK) {
        server.send(200, "application/json", "{\"success\":true}");
    } else {
        server.send(500, "application/json", "{\"success\":false,\"message\":\"Failed to delete\"}");
    }
}

void handleTemplateCount() {
    fingerSensor.getTemplateCount();
    String response = "{\"count\":" + String(fingerSensor.templateCount) + "}";
    server.send(200, "application/json", response);
}

// Helper function to enroll a new fingerprint
int enrollFinger(int id) {
    int p = -1;
    for (int i = 0; i < 2; i++) {
        p = fingerSensor.getImage();
        if (p != FINGERPRINT_OK) return -1;

        p = fingerSensor.image2Tz(i + 1);
        if (p != FINGERPRINT_OK) return -2;

        if (i == 0) {
            p = fingerSensor.getImage();
            if (p != FINGERPRINT_NOFINGER) return -3;
        }
    }

    p = fingerSensor.createModel();
    if (p != FINGERPRINT_OK) return -4;

    p = fingerSensor.storeModel(id);
    if (p != FINGERPRINT_OK) return -5;

    return 1;
}

void handleStartEnrollment() {
    if (enrollmentInProgress) {
        server.send(400, "application/json", "{\"success\":false,\"message\":\"Enrollment already in progress\"}");
        return;
    }

    enrollmentInProgress = true;
    enrollmentProgress = 0;
    lastEnrollmentStatus = FINGERPRINT_NOFINGER;
    
    server.send(200, "application/json", "{\"success\":true,\"message\":\"Enrollment started\"}");
}

void handleEnrollmentStatus() {
    if (!enrollmentInProgress) {
        server.send(200, "application/json", 
            "{\"status\":\"error\",\"progress\":0,\"message\":\"No enrollment in progress\"}");
        return;
    }

    StaticJsonDocument<512> doc;
    String status;
    String message;

    if (lastEnrollmentStatus == FINGERPRINT_NOFINGER) {
        uint8_t p = fingerSensor.getImage();
        if (p == FINGERPRINT_OK) {
            lastEnrollmentStatus = p;
            enrollmentProgress = 25;
            status = "in_progress";
            message = "First scan captured";
        } else {
            status = "waiting";
            message = "Place finger on sensor";
        }
    }
    else if (lastEnrollmentStatus == FINGERPRINT_OK && enrollmentProgress == 25) {
        uint8_t p = fingerSensor.image2Tz(1);
        if (p == FINGERPRINT_OK) {
            lastEnrollmentStatus = p;
            enrollmentProgress = 50;
            status = "in_progress";
            message = "Remove finger";
        } else {
            status = "error";
            message = "Failed to process first scan";
            enrollmentInProgress = false;
        }
    }
    else if (lastEnrollmentStatus == FINGERPRINT_OK && enrollmentProgress == 50) {
        uint8_t p = fingerSensor.getImage();
        if (p == FINGERPRINT_NOFINGER) {
            lastEnrollmentStatus = p;
            enrollmentProgress = 60;
            status = "waiting";
            message = "Place same finger again";
        }
    }
    else if (lastEnrollmentStatus == FINGERPRINT_NOFINGER && enrollmentProgress == 60) {
        uint8_t p = fingerSensor.getImage();
        if (p == FINGERPRINT_OK) {
            lastEnrollmentStatus = p;
            enrollmentProgress = 75;
            status = "in_progress";
            message = "Second scan captured";
        }
    }
    else if (lastEnrollmentStatus == FINGERPRINT_OK && enrollmentProgress == 75) {
        uint8_t p = fingerSensor.image2Tz(2);
        if (p == FINGERPRINT_OK) {
            lastEnrollmentStatus = p;
            enrollmentProgress = 85;
            status = "in_progress";
            message = "Creating model";

            p = fingerSensor.createModel();
            if (p == FINGERPRINT_OK) {
                enrollmentProgress = 100;
                status = "complete";
                message = "Enrollment complete";
                enrollmentInProgress = false;

                // Add template data to response
                JsonObject templateData = doc.createNestedObject("template_data");
                templateData["size"] = 512;  // Example size
                templateData["data"] = "base64_encoded_template_here";  // You would need to implement actual template export
            } else {
                status = "error";
                message = "Failed to create model";
                enrollmentInProgress = false;
            }
        } else {
            status = "error";
            message = "Failed to process second scan";
            enrollmentInProgress = false;
        }
    }

    doc["status"] = status;
    doc["progress"] = enrollmentProgress;
    doc["message"] = message;

    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}
