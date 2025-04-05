import logging
import json
import random
from datetime import datetime
from models import Attendance, Student, Course
from app import db

logger = logging.getLogger(__name__)

class AttendanceManager:
    """
    Class to manage attendance records and synchronization
    """
    
    def __init__(self):
        """Initialize the attendance manager"""
        self.last_sync_time = None
    
    def record_attendance(self, student_id, course_id, status='present'):
        """
        Record a new attendance entry
        
        Args:
            student_id (int): Database ID of the student
            course_id (int): Database ID of the course
            status (str): Attendance status ('present', 'late', 'absent')
            
        Returns:
            Attendance: The created attendance record or None if failed
        """
        try:
            # Validate student and course existence
            student = Student.query.get(student_id)
            course = Course.query.get(course_id)
            
            if not student or not course:
                logger.error(f"Student ID {student_id} or Course ID {course_id} not found")
                return None
            
            # Check if student is enrolled in the course
            if course not in student.courses:
                logger.warning(f"Student {student.student_id} is not enrolled in course {course.course_code}")
                # In a real system, you might want to handle this differently
            
            # Create new attendance record
            attendance = Attendance(
                student_id=student_id,
                course_id=course_id,
                timestamp=datetime.utcnow(),
                status=status,
                synced=False  # Mark as not synced initially
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            logger.info(f"Recorded {status} attendance for {student.first_name} {student.last_name} in {course.course_code}")
            return attendance
            
        except Exception as e:
            logger.error(f"Error recording attendance: {str(e)}")
            db.session.rollback()
            return None
    
    def get_unsynced_records(self):
        """
        Get all attendance records that have not been synced
        
        Returns:
            list: List of unsynced Attendance objects
        """
        return Attendance.query.filter_by(synced=False).all()
    
    def mark_as_synced(self, attendance_ids):
        """
        Mark attendance records as synced
        
        Args:
            attendance_ids (list): List of attendance record IDs to mark as synced
            
        Returns:
            int: Number of records marked as synced
        """
        try:
            count = 0
            for attendance_id in attendance_ids:
                attendance = Attendance.query.get(attendance_id)
                if attendance:
                    attendance.synced = True
                    count += 1
            
            db.session.commit()
            logger.info(f"Marked {count} attendance records as synced")
            return count
            
        except Exception as e:
            logger.error(f"Error marking records as synced: {str(e)}")
            db.session.rollback()
            return 0
    
    def sync_attendance_data(self):
        """
        Synchronize unsynced attendance data with the central server
        
        Returns:
            dict: Dictionary with sync results
        """
        try:
            # Get all unsynced records
            unsynced_records = self.get_unsynced_records()
            
            if not unsynced_records:
                logger.info("No unsynced attendance records to sync")
                return {
                    'status': 'success',
                    'message': 'No records to sync',
                    'count': 0
                }
            
            # In a real implementation, this would send the records to a remote server
            # For simulation, we'll just mark them as synced
            
            # Prepare records for sync
            attendance_ids = [record.id for record in unsynced_records]
            attendance_data = []
            
            for record in unsynced_records:
                student = Student.query.get(record.student_id)
                attendance_data.append({
                    'id': record.id,
                    'student_id': student.student_id,
                    'course_id': record.course_id,
                    'timestamp': record.timestamp.isoformat(),
                    'status': record.status
                })
            
            # Simulate API request to sync data
            # In a real system, this would make an HTTP request to the server
            logger.info(f"Syncing {len(attendance_data)} attendance records...")
            
            # Simulate network delay and random success
            import time
            time.sleep(1)  # Simulate network delay
            
            # Simulate 90% success rate for sync
            if random.random() < 0.9:
                # Success
                self.mark_as_synced(attendance_ids)
                self.last_sync_time = datetime.utcnow()
                
                return {
                    'status': 'success',
                    'message': 'Sync completed successfully',
                    'count': len(attendance_ids),
                    'sync_time': self.last_sync_time.isoformat()
                }
            else:
                # Simulated failure
                return {
                    'status': 'error',
                    'message': 'Network error during sync',
                    'count': 0
                }
            
        except Exception as e:
            logger.error(f"Error during sync: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error during sync: {str(e)}',
                'count': 0
            }
    
    def get_attendance_statistics(self, course_id=None, start_date=None, end_date=None):
        """
        Get attendance statistics for analysis
        
        Args:
            course_id (int, optional): Filter by course ID
            start_date (datetime, optional): Start date for filtering
            end_date (datetime, optional): End date for filtering
            
        Returns:
            dict: Dictionary with attendance statistics
        """
        query = Attendance.query
        
        # Apply filters
        if course_id:
            query = query.filter_by(course_id=course_id)
        
        if start_date:
            query = query.filter(Attendance.timestamp >= start_date)
        
        if end_date:
            query = query.filter(Attendance.timestamp <= end_date)
        
        # Get counts by status
        total_count = query.count()
        present_count = query.filter_by(status='present').count()
        late_count = query.filter_by(status='late').count()
        absent_count = query.filter_by(status='absent').count()
        
        # Calculate percentages
        present_percent = (present_count / total_count * 100) if total_count > 0 else 0
        late_percent = (late_count / total_count * 100) if total_count > 0 else 0
        absent_percent = (absent_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'total_records': total_count,
            'status_counts': {
                'present': present_count,
                'late': late_count,
                'absent': absent_count
            },
            'percentages': {
                'present': round(present_percent, 2),
                'late': round(late_percent, 2),
                'absent': round(absent_percent, 2)
            }
        }
