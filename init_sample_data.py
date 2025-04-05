"""
Initialize sample data for the IoT-based Fingerprint Attendance System
This script will create sample users, students, courses, and attendance records
"""

import os
import random
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Student, Course, Attendance, Fingerprint
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin_user():
    """Create an admin user if none exists"""
    admin = User.query.filter_by(is_admin=True).first()
    
    if admin is None:
        logger.info("Creating admin user...")
        admin = User(
            username="admin",
            email="admin@example.com",
            is_admin=True
        )
        admin.password_hash = generate_password_hash("admin123")
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin user created. Username: admin, Password: admin123")
    else:
        logger.info(f"Admin user already exists with username: {admin.username}. Using existing admin.")

def create_sample_courses():
    """Create sample courses"""
    # Only create courses if none exist
    if Course.query.count() == 0:
        logger.info("Creating sample courses...")
        
        # Get the admin user (any admin)
        admin = User.query.filter_by(is_admin=True).first()
        
        if admin is None:
            logger.error("No admin user found. Cannot create courses without an admin user.")
            return
            
        logger.info(f"Using admin user: {admin.username} (ID: {admin.id})")
        
        # Sample courses
        courses = [
            {
                "course_code": "CS101",
                "title": "Introduction to Computer Science",
                "description": "Fundamental concepts of computer science and programming",
                "user_id": admin.id
            },
            {
                "course_code": "CS201",
                "title": "Data Structures and Algorithms",
                "description": "Study of data structures and algorithms for solving computational problems",
                "user_id": admin.id
            },
            {
                "course_code": "CS301",
                "title": "Database Systems",
                "description": "Introduction to database design, implementation and management",
                "user_id": admin.id
            },
            {
                "course_code": "CS401",
                "title": "Artificial Intelligence",
                "description": "Introduction to AI concepts, algorithms and applications",
                "user_id": admin.id
            },
            {
                "course_code": "MATH101",
                "title": "Calculus I",
                "description": "Introduction to differential and integral calculus",
                "user_id": admin.id
            },
        ]
        
        for course_data in courses:
            course = Course(**course_data)
            db.session.add(course)
        
        db.session.commit()
        logger.info(f"Created {len(courses)} sample courses")
    else:
        logger.info("Courses already exist. Skipping...")

def create_sample_students():
    """Create sample students and enroll them in courses"""
    # Only create students if none exist
    if Student.query.count() == 0:
        logger.info("Creating sample students...")
        
        # Sample students
        students_data = [
            {
                "student_id": "S00001",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
            },
            {
                "student_id": "S00002",
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
            },
            {
                "student_id": "S00003",
                "first_name": "Michael",
                "last_name": "Johnson",
                "email": "michael.johnson@example.com",
            },
            {
                "student_id": "S00004",
                "first_name": "Emily",
                "last_name": "Brown",
                "email": "emily.brown@example.com",
            },
            {
                "student_id": "S00005",
                "first_name": "David",
                "last_name": "Wilson",
                "email": "david.wilson@example.com",
            },
            {
                "student_id": "S00006",
                "first_name": "Sarah",
                "last_name": "Taylor",
                "email": "sarah.taylor@example.com",
            },
            {
                "student_id": "S00007",
                "first_name": "James",
                "last_name": "Anderson",
                "email": "james.anderson@example.com",
            },
            {
                "student_id": "S00008",
                "first_name": "Emma",
                "last_name": "Thomas",
                "email": "emma.thomas@example.com",
            },
            {
                "student_id": "S00009",
                "first_name": "Robert",
                "last_name": "Jackson",
                "email": "robert.jackson@example.com",
            },
            {
                "student_id": "S00010",
                "first_name": "Olivia",
                "last_name": "White",
                "email": "olivia.white@example.com",
            },
        ]
        
        students = []
        for student_data in students_data:
            student = Student(**student_data)
            db.session.add(student)
            students.append(student)
        
        # Commit to get student IDs
        db.session.commit()
        
        # Get all courses
        courses = Course.query.all()
        
        # Enroll students in courses (each student in 2-3 random courses)
        for student in students:
            num_courses = random.randint(2, 3)
            selected_courses = random.sample(courses, num_courses)
            for course in selected_courses:
                student.courses.append(course)
            
            # Create a simulated fingerprint for each student
            finger_id = random.randint(0, 9)  # Random finger ID
            fingerprint = Fingerprint(
                student_id=student.id,
                finger_id=finger_id,
                template_data=os.urandom(512)  # Random 512 bytes as template data
            )
            db.session.add(fingerprint)
        
        db.session.commit()
        logger.info(f"Created {len(students_data)} sample students with course enrollments and fingerprints")
    else:
        logger.info("Students already exist. Skipping...")

def create_sample_attendance():
    """Create sample attendance records for the past 2 weeks"""
    # Only create attendance records if none exist
    if Attendance.query.count() == 0:
        logger.info("Creating sample attendance records...")
        
        # Get all students and courses
        students = Student.query.all()
        
        # For the past 14 days
        today = datetime.utcnow().date()
        for day_offset in range(14, 0, -1):  # Past 14 days, excluding today
            date = today - timedelta(days=day_offset)
            # Only add records for weekdays (Monday=0, Sunday=6)
            if date.weekday() < 5:  # Weekdays only
                # For each student
                for student in students:
                    # Get the courses this student is enrolled in
                    student_courses = student.courses
                    
                    # For each of their courses, create attendance with 80% chance of being present
                    for course in student_courses:
                        # Random status with weighted probability
                        status_options = ['present', 'late', 'absent']
                        weights = [0.8, 0.1, 0.1]  # 80% present, 10% late, 10% absent
                        status = random.choices(status_options, weights=weights, k=1)[0]
                        
                        # Generate a timestamp for this day (between 8 AM and 4 PM)
                        hour = random.randint(8, 16)
                        minute = random.randint(0, 59)
                        timestamp = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                        
                        # Create the attendance record
                        attendance = Attendance(
                            student_id=student.id,
                            course_id=course.id,
                            timestamp=timestamp,
                            status=status,
                            synced=True
                        )
                        db.session.add(attendance)
        
        db.session.commit()
        logger.info(f"Created sample attendance records for the past 2 weeks")
    else:
        logger.info("Attendance records already exist. Skipping...")

def main():
    """Main function to initialize sample data"""
    logger.info("Starting sample data initialization...")
    
    with app.app_context():
        # Create admin user
        create_admin_user()
        
        # Create courses
        create_sample_courses()
        
        # Create students
        create_sample_students()
        
        # Create attendance records
        create_sample_attendance()
        
        logger.info("Sample data initialization complete!")

if __name__ == "__main__":
    main()