#!/usr/bin/env python3
"""
Test script to validate enrollment restrictions for the attendance system
"""

import requests
import json
import sys
from pprint import pprint

BASE_URL = "http://localhost:5000/api"

def test_get_student_courses(student_id=1):
    """Test getting a student's enrolled courses"""
    print(f"\n=== Testing Get Student with ID {student_id} ===")
    response = requests.get(f"{BASE_URL}/students")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    student = None
    
    for s in data['students']:
        if s['id'] == student_id:
            student = s
            break
    
    if not student:
        print(f"Student with ID {student_id} not found")
        return None
    
    print(f"Student: {student['name']} (ID: {student['id']})")
    print("Enrolled Courses:")
    for course in student['courses']:
        print(f"  - {course['code']}: {course['title']} (ID: {course['id']})")
    
    return student

def test_get_all_courses():
    """Test getting all available courses"""
    print("\n=== Testing Get All Courses ===")
    response = requests.get(f"{BASE_URL}/courses")
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None
    
    data = response.json()
    print(f"Found {data['count']} courses:")
    
    courses = data['courses']
    for course in courses:
        print(f"  - {course['code']}: {course['title']} (ID: {course['id']})")
    
    return courses

def test_record_attendance_enrolled(student_id=1, course_id=1):
    """Test recording attendance for a course the student is enrolled in"""
    print(f"\n=== Testing Record Attendance (Enrolled) ===")
    print(f"Student ID: {student_id}, Course ID: {course_id}")
    
    payload = {
        "student_id": student_id,
        "course_id": course_id,
        "status": "present"
    }
    
    response = requests.post(
        f"{BASE_URL}/attendance",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        pprint(data)
        return data
    except json.JSONDecodeError:
        print(response.text)
        return None

def test_record_attendance_not_enrolled(student_id=1, not_enrolled_course_id=None):
    """Test recording attendance for a course the student is NOT enrolled in"""
    # First find a course the student is not enrolled in
    if not_enrolled_course_id is None:
        student = test_get_student_courses(student_id)
        all_courses = test_get_all_courses()
        
        if not student or not all_courses:
            print("Error: Could not fetch student or course data")
            return None
        
        # Find a course the student is not enrolled in
        enrolled_course_ids = [c['id'] for c in student['courses']]
        not_enrolled_courses = [c for c in all_courses if c['id'] not in enrolled_course_ids]
        
        if not not_enrolled_courses:
            print("Error: Student is enrolled in all available courses")
            return None
        
        not_enrolled_course_id = not_enrolled_courses[0]['id']
    
    print(f"\n=== Testing Record Attendance (NOT Enrolled) ===")
    print(f"Student ID: {student_id}, Course ID: {not_enrolled_course_id}")
    
    payload = {
        "student_id": student_id,
        "course_id": not_enrolled_course_id,
        "status": "present"
    }
    
    response = requests.post(
        f"{BASE_URL}/attendance",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        pprint(data)
        return data
    except json.JSONDecodeError:
        print(response.text)
        return None

def main():
    """Main function to run tests"""
    # Test with student ID 1
    student_id = 1
    
    # Test with a student that is enrolled in at least one course
    student = test_get_student_courses(student_id)
    
    if not student or not student['courses']:
        print("Error: Student has no enrolled courses")
        sys.exit(1)
    
    # Test attendance recording for a course the student is enrolled in
    enrolled_course_id = student['courses'][0]['id']
    test_record_attendance_enrolled(student_id, enrolled_course_id)
    
    # Test attendance recording for a course the student is NOT enrolled in
    test_record_attendance_not_enrolled(student_id)

if __name__ == "__main__":
    main()