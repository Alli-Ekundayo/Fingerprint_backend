// Dashboard charts and statistics functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize attendance chart if it exists
    const attendanceChartElem = document.getElementById('attendanceChart');
    if (attendanceChartElem) {
        initializeAttendanceChart();
    }
    
    // Initialize course stats chart if it exists
    const courseStatsElem = document.getElementById('courseStatsChart');
    if (courseStatsElem) {
        initializeCourseStatsChart();
    }
});

/**
 * Initialize the weekly attendance chart
 */
function initializeAttendanceChart() {
    // Get the chart element
    const ctx = document.getElementById('attendanceChart').getContext('2d');
    
    // Get data from the data attribute
    const chartDataElem = document.getElementById('attendanceChartData');
    let chartData = [];
    
    if (chartDataElem && chartDataElem.dataset.chartData) {
        try {
            chartData = JSON.parse(chartDataElem.dataset.chartData);
        } catch (e) {
            console.error('Error parsing chart data:', e);
            chartData = [];
        }
    } else {
        // Sample data for development if no data is provided
        chartData = [
            { date: '2023-05-01', count: 15 },
            { date: '2023-05-02', count: 18 },
            { date: '2023-05-03', count: 14 },
            { date: '2023-05-04', count: 16 },
            { date: '2023-05-05', count: 12 },
            { date: '2023-05-06', count: 0 },
            { date: '2023-05-07', count: 0 }
        ];
    }
    
    // Prepare labels and data for chart
    const labels = chartData.map(item => {
        const date = new Date(item.date);
        return date.toLocaleDateString('en-US', { weekday: 'short' });
    });
    
    const data = chartData.map(item => item.count);
    
    // Create chart
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily Attendance',
                data: data,
                backgroundColor: 'rgba(13, 110, 253, 0.5)',
                borderColor: 'rgba(13, 110, 253, 1)',
                borderWidth: 1,
                borderRadius: 5,
                maxBarThickness: 50
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        label: function(context) {
                            return `Attendance: ${context.raw} students`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: 'Number of Students'
                    }
                }
            }
        }
    });
}

/**
 * Initialize the course statistics chart
 */
function initializeCourseStatsChart() {
    // Get the chart element
    const ctx = document.getElementById('courseStatsChart').getContext('2d');
    
    // Get data from the data attribute
    const chartDataElem = document.getElementById('courseStatsData');
    let chartData = [];
    
    if (chartDataElem && chartDataElem.dataset.chartData) {
        try {
            chartData = JSON.parse(chartDataElem.dataset.chartData);
        } catch (e) {
            console.error('Error parsing course stats data:', e);
            chartData = [];
        }
    } else {
        // Sample data for development if no data is provided
        chartData = [
            { course: 'CS101', rate: 85 },
            { course: 'MATH201', rate: 72 },
            { course: 'ENG105', rate: 90 },
            { course: 'PHYS202', rate: 78 }
        ];
    }
    
    // Prepare labels and data for chart
    const labels = chartData.map(item => item.course);
    const data = chartData.map(item => item.rate);
    
    // Create chart
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    'rgba(13, 110, 253, 0.7)',
                    'rgba(25, 135, 84, 0.7)',
                    'rgba(13, 202, 240, 0.7)',
                    'rgba(255, 193, 7, 0.7)',
                    'rgba(220, 53, 69, 0.7)'
                ],
                borderColor: [
                    'rgba(13, 110, 253, 1)',
                    'rgba(25, 135, 84, 1)',
                    'rgba(13, 202, 240, 1)',
                    'rgba(255, 193, 7, 1)',
                    'rgba(220, 53, 69, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw}% attendance`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Update attendance statistics via AJAX
 */
function refreshStatistics() {
    // Show loading indicator
    document.getElementById('refreshBtn').classList.add('disabled');
    document.getElementById('refreshSpinner').classList.remove('d-none');
    
    // Make AJAX request to get updated statistics
    fetch('/api/statistics')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update stats on the page
                document.getElementById('studentCount').textContent = data.counts.students;
                document.getElementById('courseCount').textContent = data.counts.courses;
                document.getElementById('attendanceCount').textContent = data.counts.attendance_records;
                
                // Create a toast notification
                showToast('Statistics updated successfully', 'success');
                
                // Reload charts with new data
                initializeAttendanceChart();
                initializeCourseStatsChart();
            } else {
                showToast('Error updating statistics', 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching statistics:', error);
            showToast('Error updating statistics', 'error');
        })
        .finally(() => {
            // Hide loading indicator
            document.getElementById('refreshBtn').classList.remove('disabled');
            document.getElementById('refreshSpinner').classList.add('d-none');
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
