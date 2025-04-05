// Fingerprint scanning and attendance recording functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize fingerprint enrollment if on enrollment page
    const enrollmentForm = document.getElementById('fingerprintEnrollmentForm');
    if (enrollmentForm) {
        initializeEnrollment();
    }
    
    // Initialize fingerprint scanning if on scan page
    const scanForm = document.getElementById('fingerprintScanForm');
    if (scanForm) {
        initializeScanning();
    }
});

/**
 * Initialize fingerprint enrollment process
 */
function initializeEnrollment() {
    const enrollmentStatus = document.getElementById('enrollmentStatus');
    const progressBar = document.getElementById('enrollmentProgress');
    const startEnrollBtn = document.getElementById('startEnrollBtn');
    const cancelEnrollBtn = document.getElementById('cancelEnrollBtn');
    const successIcon = document.getElementById('enrollSuccessIcon');
    const fingerprintAnimation = document.querySelector('.fingerprint-animation');
    
    // If enrollment process has started
    if (document.body.classList.contains('enrolling')) {
        let enrollmentComplete = false;
        let enrollmentFailed = false;
        
        // Poll enrollment status
        const statusInterval = setInterval(function() {
            if (enrollmentComplete || enrollmentFailed) {
                clearInterval(statusInterval);
                return;
            }
            
            fetch('/enroll/status')
                .then(response => response.json())
                .then(data => {
                    // Update progress bar
                    progressBar.style.width = data.progress + '%';
                    progressBar.setAttribute('aria-valuenow', data.progress);
                    
                    // Update status message
                    enrollmentStatus.textContent = data.message;
                    
                    if (data.status === 'waiting') {
                        fingerprintAnimation.classList.remove('scanning');
                    } else if (data.status === 'in_progress') {
                        fingerprintAnimation.classList.add('scanning');
                    } else if (data.status === 'complete') {
                        enrollmentComplete = true;
                        fingerprintAnimation.classList.remove('scanning');
                        
                        // Show success icon
                        if (successIcon) {
                            successIcon.classList.remove('d-none');
                        }
                        
                        // Enable and show the "Done" button
                        cancelEnrollBtn.textContent = 'Done';
                        cancelEnrollBtn.classList.remove('btn-secondary');
                        cancelEnrollBtn.classList.add('btn-success');
                        
                        // Show success message
                        showToast('Enrollment completed successfully!', 'success');
                    } else if (data.status === 'error') {
                        enrollmentFailed = true;
                        showToast('Enrollment failed: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error checking enrollment status:', error);
                });
        }, 1000);
    }
    
    // Setup start enrollment button
    if (startEnrollBtn) {
        startEnrollBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const form = document.getElementById('fingerprintEnrollmentForm');
            form.submit();
        });
    }
}

/**
 * Initialize fingerprint scanning for attendance
 */
function initializeScanning() {
    const scanForm = document.getElementById('fingerprintScanForm');
    const scanStatus = document.getElementById('scanStatus');
    const startScanBtn = document.getElementById('startScanBtn');
    const courseSelect = document.getElementById('courseSelect');
    const fingerprintAnimation = document.querySelector('.fingerprint-animation');
    
    // Setup scan button
    if (startScanBtn) {
        startScanBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Validate course selection
            if (!courseSelect.value) {
                showToast('Please select a course first', 'error');
                return;
            }
            
            // Start scanning animation
            fingerprintAnimation.classList.add('scanning');
            scanStatus.textContent = 'Place finger on sensor...';
            startScanBtn.disabled = true;
            
            // Send scan request
            const formData = new FormData();
            formData.append('course_id', courseSelect.value);
            
            fetch('/scan/verify', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                fingerprintAnimation.classList.remove('scanning');
                startScanBtn.disabled = false;
                
                if (data.status === 'success') {
                    scanStatus.textContent = data.message;
                    scanStatus.className = 'text-success';
                    showToast(data.message, 'success');
                } else {
                    scanStatus.textContent = data.message;
                    scanStatus.className = 'text-danger';
                    showToast(data.message, 'error');
                }
                
                // Reset after 5 seconds
                setTimeout(function() {
                    scanStatus.textContent = 'Ready to scan';
                    scanStatus.className = 'text-info';
                }, 5000);
            })
            .catch(error => {
                console.error('Error during fingerprint verification:', error);
                fingerprintAnimation.classList.remove('scanning');
                startScanBtn.disabled = false;
                scanStatus.textContent = 'Error during scan';
                scanStatus.className = 'text-danger';
                showToast('Error during fingerprint scan', 'error');
            });
        });
    }
}

/**
 * Sync attendance data with the server
 */
function syncAttendanceData() {
    // Show syncing indicator
    document.getElementById('syncBtn').classList.add('disabled');
    document.getElementById('syncSpinner').classList.remove('d-none');
    
    fetch('/sync')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.text();
        })
        .then(html => {
            // Update the page with the new content
            // This is a simple approach - in a more complex app, you might
            // want to use fetch with JSON and update specific elements
            document.location.reload();
        })
        .catch(error => {
            console.error('Error syncing attendance data:', error);
            showToast('Error syncing attendance data', 'error');
            
            // Hide syncing indicator
            document.getElementById('syncBtn').classList.remove('disabled');
            document.getElementById('syncSpinner').classList.add('d-none');
        });
}

/**
 * Display a toast notification
 * @param {string} message - Message to display
 * @param {string} type - 'success', 'error', or 'info'
 */
function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        // Create toast container if it doesn't exist
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    // Get BS5 color class based on type
    let bgClass = 'bg-info';
    if (type === 'success') bgClass = 'bg-success';
    if (type === 'error') bgClass = 'bg-danger';
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = `toast ${bgClass} text-white`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">Attendance System</strong>
            <small>Just now</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add toast to container
    document.querySelector('.toast-container').appendChild(toastEl);
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
    toast.show();
    
    // Remove the toast after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}
