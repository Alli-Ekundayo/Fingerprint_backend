import logging
import time
import random
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class FingerprintSensor:
    """
    Class to interface with fingerprint sensor hardware.
    
    For this implementation, we're simulating the sensor behavior
    since we don't have actual hardware connected.
    """
    
    def __init__(self):
        """Initialize the fingerprint sensor interface"""
        self.initialized = False
        self.enrolling = False
        self.enrollment_stage = 0
        self.stored_templates = {}  # In a real system, these would be stored in a database
        
        # Simulation state
        self._simulation_state = {
            'last_operation': None,
            'last_operation_time': None,
            'enrollment_progress': 0,
            'sample_fingerprint_data': b'SIMULATED_FINGERPRINT_TEMPLATE_DATA'
        }
        
        # Attempt to initialize the sensor (simulated)
        self._initialize()
    
    def _initialize(self):
        """Initialize the fingerprint sensor hardware (simulated)"""
        logger.info("Initializing fingerprint sensor...")
        
        # In a real implementation, this would contain code to
        # communicate with the actual fingerprint sensor hardware
        
        # Simulate initialization
        time.sleep(0.5)  # Simulate hardware initialization time
        self.initialized = True
        logger.info("Fingerprint sensor initialized successfully")
    
    def start_enrollment(self):
        """Start the fingerprint enrollment process"""
        if not self.initialized:
            logger.error("Cannot start enrollment: Sensor not initialized")
            return False
        
        logger.info("Starting fingerprint enrollment process")
        self.enrolling = True
        self.enrollment_stage = 1
        self._simulation_state['enrollment_progress'] = 0
        self._simulation_state['last_operation'] = 'start_enrollment'
        self._simulation_state['last_operation_time'] = datetime.utcnow()
        
        return True
    
    def get_enrollment_status(self):
        """
        Get the current status of enrollment
        
        Returns a dictionary with:
        - status: 'waiting', 'in_progress', 'complete', or 'error'
        - message: A status message
        - progress: Percentage of enrollment completed (0-100)
        - data: Fingerprint template data if complete
        """
        if not self.enrolling:
            return {
                'status': 'error',
                'message': 'No enrollment in progress',
                'progress': 0
            }
        
        # Simulate enrollment progress
        current_time = datetime.utcnow()
        elapsed = (current_time - self._simulation_state['last_operation_time']).total_seconds()
        
        # Simulate enrollment stages
        if self.enrollment_stage == 1:
            # First fingerprint capture
            if elapsed < 2:
                # Still waiting for finger
                return {
                    'status': 'waiting',
                    'message': 'Place finger on sensor',
                    'progress': 0
                }
            elif elapsed < 4:
                # Capturing fingerprint
                progress = min(100, int((elapsed - 2) * 50))
                return {
                    'status': 'in_progress',
                    'message': 'Capturing fingerprint...',
                    'progress': progress
                }
            else:
                # First capture complete
                self.enrollment_stage = 2
                self._simulation_state['last_operation_time'] = current_time
                return {
                    'status': 'waiting',
                    'message': 'Remove finger and place again for confirmation',
                    'progress': 50
                }
        
        elif self.enrollment_stage == 2:
            # Second fingerprint capture for confirmation
            if elapsed < 2:
                # Waiting for finger again
                return {
                    'status': 'waiting',
                    'message': 'Place finger on sensor again',
                    'progress': 50
                }
            elif elapsed < 4:
                # Capturing second sample
                progress = min(100, 50 + int((elapsed - 2) * 25))
                return {
                    'status': 'in_progress',
                    'message': 'Capturing second sample...',
                    'progress': progress
                }
            else:
                # Processing and comparing samples
                self.enrollment_stage = 3
                self._simulation_state['last_operation_time'] = current_time
                
                # Simulate processing time
                if elapsed < 5:
                    return {
                        'status': 'in_progress',
                        'message': 'Processing and comparing samples...',
                        'progress': 95
                    }
                else:
                    # Enrollment complete
                    self.enrolling = False
                    
                    # Generate simulated template data
                    template_data = self._simulation_state['sample_fingerprint_data']
                    
                    return {
                        'status': 'complete',
                        'message': 'Enrollment successful!',
                        'progress': 100,
                        'data': template_data
                    }
        
        # Should not reach here
        return {
            'status': 'error',
            'message': 'Unknown enrollment state',
            'progress': 0
        }
    
    def verify_fingerprint(self):
        """
        Verify a fingerprint against stored templates
        
        Returns a dictionary with:
        - status: 'waiting', 'scanning', 'match', 'no_match', or 'error'
        - message: A status message
        - student_id: The ID of the matched student (if match)
        """
        if not self.initialized:
            logger.error("Cannot verify fingerprint: Sensor not initialized")
            return {
                'status': 'error',
                'message': 'Sensor not initialized'
            }
        
        # In a real implementation, this would capture a fingerprint
        # and compare it against stored templates
        
        # For simulation, randomly decide if we have a match
        # with 80% success rate
        time.sleep(2)  # Simulate scanning time
        
        if random.random() < 0.8:  # 80% success rate
            # Simulate a successful match
            # In a real system, we would identify which student matched
            
            # For simulation, randomly select a student ID between 1 and 5
            student_id = random.randint(1, 5)
            
            return {
                'status': 'match',
                'message': 'Fingerprint matched',
                'student_id': student_id
            }
        else:
            # No match
            return {
                'status': 'no_match',
                'message': 'No matching fingerprint found'
            }
    
    def cancel_operation(self):
        """Cancel any ongoing operation"""
        self.enrolling = False
        self.enrollment_stage = 0
        logger.info("Fingerprint operation cancelled")
        return True
    
    def get_status(self):
        """Get the current status of the sensor"""
        if not self.initialized:
            return {
                'status': 'not_initialized',
                'message': 'Sensor not initialized'
            }
        
        if self.enrolling:
            return {
                'status': 'enrolling',
                'message': f'Enrollment in progress (stage {self.enrollment_stage})'
            }
        
        return {
            'status': 'ready',
            'message': 'Sensor ready'
        }
