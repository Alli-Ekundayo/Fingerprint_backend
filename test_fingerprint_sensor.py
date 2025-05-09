import unittest
from unittest.mock import patch, MagicMock
from flask import url_for
from app import create_app, db
from models import Student, Fingerprint, Course
from datetime import datetime

class TestFingerprintRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test data
        self.student = Student(
            student_id="TEST001",
            first_name="Test",
            last_name="Student",
            email="test@example.com"
        )
        db.session.add(self.student)
        
        self.course = Course(
            course_code="TEST101",
            title="Test Course",
            description="Test Description"
        )
        db.session.add(self.course)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('fingerprint_sensor_module.FingerPrintSensor.connect')
    @patch('fingerprint_sensor_module.FingerPrintSensor.verify_finger')
    def test_verify_fingerprint(self, mock_verify, mock_connect):
        # Mock successful connection
        mock_connect.return_value = True
        
        # Mock successful verification
        mock_verify.return_value = {
            'success': True,
            'finger_id': 1,
            'confidence': 100
        }
        
        # Create a test fingerprint record
        fingerprint = Fingerprint(
            student_id=self.student.id,
            finger_id=1,
            created_at=datetime.utcnow()
        )
        db.session.add(fingerprint)
        db.session.commit()
        
        # Test verification endpoint
        response = self.client.post('/scan/verify', data={
            'course_id': self.course.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn(self.student.first_name, data['message'])

    @patch('fingerprint_sensor_module.FingerPrintSensor.connect')
    @patch('fingerprint_sensor_module.FingerPrintSensor.enroll_finger')
    def test_enrollment_process(self, mock_enroll, mock_connect):
        # Mock successful connection
        mock_connect.return_value = True
        
        # Mock successful enrollment
        mock_enroll.return_value = {
            'success': True,
            'message': 'Enrollment successful'
        }
        
        with self.client.session_transaction() as session:
            session['enrollment_student_id'] = self.student.id
            session['enrollment_finger_id'] = 1
        
        # Test enrollment process endpoint
        response = self.client.post('/enroll/process')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'success')
        self.assertIn(self.student.first_name, data['message'])
        
        # Verify fingerprint was stored in database
        fingerprint = Fingerprint.query.filter_by(
            student_id=self.student.id,
            finger_id=1
        ).first()
        self.assertIsNotNone(fingerprint)

    @patch('fingerprint_sensor_module.FingerPrintSensor.connect')
    @patch('fingerprint_sensor_module.FingerPrintSensor.verify_finger')
    def test_verify_fingerprint_not_enrolled(self, mock_verify, mock_connect):
        # Mock successful connection
        mock_connect.return_value = True
        
        # Mock successful verification but with unregistered finger_id
        mock_verify.return_value = {
            'success': True,
            'finger_id': 999,
            'confidence': 100
        }
        
        # Test verification endpoint
        response = self.client.post('/scan/verify', data={
            'course_id': self.course.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('not enrolled', data['message'])

    @patch('fingerprint_sensor_module.FingerPrintSensor.connect')
    def test_verify_fingerprint_connection_failed(self, mock_connect):
        # Mock failed connection
        mock_connect.return_value = False
        
        # Test verification endpoint
        response = self.client.post('/scan/verify', data={
            'course_id': self.course.id
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('Failed to connect', data['message'])

if __name__ == '__main__':
    unittest.main()