#!/usr/bin/env python3
"""
Test script to simulate API calls from an Arduino device
This script demonstrates how to interact with the Flask backend APIs
"""

import requests
import json
import time
from datetime import datetime

# Server URL - replace with your actual server URL
SERVER_URL = "http://localhost:5000"

# API endpoints
COURSES_ENDPOINT = "/api/courses"
ATTENDANCE_ENDPOINT = "/api/attendance"
VERIFY_FINGERPRINT_ENDPOINT = "/api/verify-fingerprint"

def test_get_courses():
    """Test fetching course data"""
    print("\n=== Testing GET Courses API ===")
    
    try:
        response = requests.get(f"{SERVER_URL}{COURSES_ENDPOINT}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Fetched {data['count']} courses:")
            
            for idx, course in enumerate(data['courses'], 1):
                print(f"{idx}. {course['code']} - {course['title']} (ID: {course['id']})")
            
            return data['courses']
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return []
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return []

def test_verify_fingerprint(fingerprint_id=1):
    """Test fingerprint verification API"""
    print(f"\n=== Testing Verify Fingerprint API (ID: {fingerprint_id}) ===")
    
    try:
        payload = {
            "fingerprint_id": fingerprint_id
        }
        
        response = requests.post(
            f"{SERVER_URL}{VERIFY_FINGERPRINT_ENDPOINT}", 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))
        
        if response.status_code == 200 and data.get('success'):
            return data['student']
        else:
            return None
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def test_record_attendance(student_id, course_id, status="present"):
    """Test recording attendance API"""
    print(f"\n=== Testing Record Attendance API ===")
    print(f"Student ID: {student_id}, Course ID: {course_id}, Status: {status}")
    
    try:
        # Prepare payload
        payload = {
            "student_id": student_id,
            "course_id": course_id,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send request
        response = requests.post(
            f"{SERVER_URL}{ATTENDANCE_ENDPOINT}", 
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response Status: {response.status_code}")
        data = response.json()
        print(json.dumps(data, indent=2))
        
        return response.status_code == 200 and data.get('success', False)
            
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

def simulate_fingerprint_attendance_flow():
    """Simulate the complete fingerprint attendance flow"""
    print("\n=== Simulating Complete Fingerprint Attendance Flow ===")
    
    # Step 1: Load available courses
    print("\nStep 1: Loading available courses...")
    courses = test_get_courses()
    
    if not courses:
        print("No courses available. Aborting test.")
        return
    
    selected_course = courses[0]  # Select the first course
    print(f"Selected course: {selected_course['code']} (ID: {selected_course['id']})")
    
    # Step 2: Verify fingerprint
    print("\nStep 2: Verifying fingerprint...")
    print("Simulating finger placement on sensor...")
    time.sleep(1)  # Simulate delay for scanning
    
    # Simulate successful fingerprint match
    student = test_verify_fingerprint(fingerprint_id=3)  # Try with finger_id=3 from our database
    
    if not student:
        print("Fingerprint verification failed. Aborting test.")
        return
    
    print(f"Fingerprint matched to student: {student['name']} (ID: {student['id']})")
    
    # Step 3: Record attendance
    print("\nStep 3: Recording attendance...")
    success = test_record_attendance(
        student_id=student['id'],
        course_id=selected_course['id'],
        status="present"
    )
    
    if success:
        print(f"Attendance successfully recorded for {student['name']} in {selected_course['code']}")
    else:
        print("Failed to record attendance")

if __name__ == "__main__":
    print("IoT Fingerprint Attendance System - API Test")
    print("===========================================")
    print(f"Server URL: {SERVER_URL}")
    
    # Run tests individually
    # test_get_courses()
    # test_verify_fingerprint(fingerprint_id=0)  # Try with the first fingerprint ID
    # test_record_attendance(student_id=1, course_id=1)  # Use actual IDs from your database
    
    # Simulate the complete flow
    simulate_fingerprint_attendance_flow()