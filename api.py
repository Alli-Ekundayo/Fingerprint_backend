import logging
from flask import jsonify, request, Blueprint
from flask_login import login_required
from models import Attendance, Student, Course
from app import db
from datetime import datetime
from utils import json_response

logger = logging.getLogger(__name__)

# Blueprint for API routes
api = Blueprint('api', __name__)

@api.route('/attendance', methods=['GET'])
@login_required
def get_attendance():
    """API endpoint to get attendance records"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        course_id = request.args.get('course_id')
        student_id = request.args.get('student_id')
        
        # Build query
        query = Attendance.query
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Attendance.timestamp >= start)
            except ValueError:
                return json_response({"error": "Invalid start_date format"}, 400)
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d')
                end = datetime.combine(end.date(), datetime.max.time())
                query = query.filter(Attendance.timestamp <= end)
            except ValueError:
                return json_response({"error": "Invalid end_date format"}, 400)
        
        if course_id:
            query = query.filter(Attendance.course_id == course_id)
        
        if student_id:
            # This could be a student database ID or student ID string
            try:
                # Try to parse as integer (database ID)
                query = query.filter(Attendance.student_id == int(student_id))
            except ValueError:
                # If not an integer, try to find by student ID string
                student = Student.query.filter_by(student_id=student_id).first()
                if student:
                    query = query.filter(Attendance.student_id == student.id)
                else:
                    return json_response({"error": "Student not found"}, 404)
        
        # Execute query and format results
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        # Format attendance records
        results = []
        for record in attendance_records:
            student = Student.query.get(record.student_id)
            course = Course.query.get(record.course_id)
            
            results.append({
                'id': record.id,
                'student': {
                    'id': student.id,
                    'student_id': student.student_id,
                    'name': f"{student.first_name} {student.last_name}"
                },
                'course': {
                    'id': course.id,
                    'code': course.course_code,
                    'title': course.title
                },
                'timestamp': record.timestamp.isoformat(),
                'status': record.status,
                'synced': record.synced
            })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'records': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching attendance records: {str(e)}")
        return json_response({"error": "Internal server error"}, 500)

@api.route('/attendance', methods=['POST'])
def record_attendance():
    """API endpoint to record attendance from IoT device"""
    try:
        data = request.get_json()
        
        if not data:
            return json_response({"error": "No data provided"}, 400)
        
        required_fields = ['student_id', 'course_id', 'timestamp', 'status']
        for field in required_fields:
            if field not in data:
                return json_response({"error": f"Missing required field: {field}"}, 400)
        
        # Find student by student_id string
        student = Student.query.filter_by(student_id=data['student_id']).first()
        if not student:
            return json_response({"error": "Student not found"}, 404)
        
        # Find course
        course = Course.query.get(data['course_id'])
        if not course:
            return json_response({"error": "Course not found"}, 404)
            
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(data['timestamp'])
        except ValueError:
            timestamp = datetime.utcnow()
        
        # Create attendance record
        attendance = Attendance(
            student_id=student.id,
            course_id=course.id,
            timestamp=timestamp,
            status=data['status'],
            synced=True  # This is coming from an API, so it's already synced
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'attendance_id': attendance.id,
            'message': f'Attendance recorded for {student.first_name} {student.last_name}'
        })
        
    except Exception as e:
        logger.error(f"Error recording attendance: {str(e)}")
        db.session.rollback()
        return json_response({"error": "Internal server error"}, 500)

@api.route('/students', methods=['GET'])
@login_required
def get_students():
    """API endpoint to get student list"""
    try:
        students = Student.query.all()
        
        results = []
        for student in students:
            results.append({
                'id': student.id,
                'student_id': student.student_id,
                'name': f"{student.first_name} {student.last_name}",
                'email': student.email,
                'courses': [{'id': c.id, 'code': c.course_code, 'title': c.title} for c in student.courses]
            })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'students': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching students: {str(e)}")
        return json_response({"error": "Internal server error"}, 500)

@api.route('/courses', methods=['GET'])
@login_required
def get_courses():
    """API endpoint to get course list"""
    try:
        courses = Course.query.all()
        
        results = []
        for course in courses:
            results.append({
                'id': course.id,
                'code': course.course_code,
                'title': course.title,
                'description': course.description,
                'student_count': course.students.count()
            })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'courses': results
        })
        
    except Exception as e:
        logger.error(f"Error fetching courses: {str(e)}")
        return json_response({"error": "Internal server error"}, 500)

@api.route('/statistics', methods=['GET'])
@login_required
def get_statistics():
    """API endpoint to get attendance statistics"""
    try:
        # Get total counts
        student_count = Student.query.count()
        course_count = Course.query.count()
        attendance_count = Attendance.query.count()
        
        # Get status distribution
        present_count = Attendance.query.filter_by(status='present').count()
        late_count = Attendance.query.filter_by(status='late').count()
        absent_count = Attendance.query.filter_by(status='absent').count()
        
        # Calculate percentage
        present_percent = (present_count / attendance_count * 100) if attendance_count > 0 else 0
        late_percent = (late_count / attendance_count * 100) if attendance_count > 0 else 0
        absent_percent = (absent_count / attendance_count * 100) if attendance_count > 0 else 0
        
        return jsonify({
            'success': True,
            'counts': {
                'students': student_count,
                'courses': course_count,
                'attendance_records': attendance_count
            },
            'attendance_status': {
                'present': present_count,
                'late': late_count,
                'absent': absent_count
            },
            'attendance_percentage': {
                'present': round(present_percent, 2),
                'late': round(late_percent, 2),
                'absent': round(absent_percent, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        return json_response({"error": "Internal server error"}, 500)

def register_api_routes(app):
    """Register API routes with Flask app"""
    app.register_blueprint(api, url_prefix='/api')
    logger.info("API routes registered")