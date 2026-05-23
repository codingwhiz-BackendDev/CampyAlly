// Emergency Report JavaScript
const API = '/parking/api';
const CSRF = '{{ csrf_token }}';

let selectedType = null;
let selectedSeverity = 'high';
let userLatitude = null;
let userLongitude = null;

// Safety tips by emergency type
const SAFETY_TIPS = {
    medical: [
        'Stay calm and assess the situation',
        'Check if the person is breathing and conscious',
        'Do not move the injured person unless necessary',
        'Apply pressure to any bleeding wounds',
        'Clear the area to allow medical team access'
    ],
    fire: [
        'Alert others immediately - shout "Fire!"',
        'Do NOT use elevators, use stairs only',
        'Stay low to avoid smoke inhalation',
        'If clothes catch fire, stop, drop, and roll',
        'Move to the designated assembly point'
    ],
    security: [
        'Stay alert and aware of your surroundings',
        'Move to a safe, populated area if possible',
        'Do not confront the threat directly',
        'Lock doors and windows if indoors',
        'Call security and provide clear location details'
    ],
    missing: [
        'Note the child\'s last known location and time',
        'Check with nearby staff and security',
        'Provide a recent photo if available',
        'Describe clothing and distinctive features',
        'Stay at the last known location if safe to do so'
    ],
    traffic: [
        'Turn on hazard lights if in a vehicle',
        'Move to a safe location away from traffic',
        'Check for injuries and call for help',
        'Do not move injured persons unless in danger',
        'Exchange information with other parties if safe'
    ],
    stampede: [
        'Stay calm and do not panic',
        'Move sideways with the crowd flow, not against it',
        'Protect your head and chest with your arms',
        'Seek shelter behind a solid object if possible',
        'Help others only if you can do so safely'
    ],
    other: [
        'Assess the situation calmly',
        'Report all relevant details clearly',
        'Follow instructions from emergency responders',
        'Stay in a safe location until help arrives',
        'Keep your phone accessible for updates'
    ]
};

function selectType(btn, type) {
    // Remove selected class from all buttons
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('selected'));
    
    // Add selected class to clicked button
    btn.classList.add('selected');
    
    // Store selected type
    selectedType = type;
    
    // Show extended form
    document.getElementById('form-extended').style.display = 'block';
    
    // Update safety tips
    updateSafetyTips(type);
    
    // Scroll to extended form
    setTimeout(() => {
        document.getElementById('form-extended').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

function selectSeverity(btn, severity) {
    // Remove selected class from all buttons
    document.querySelectorAll('.sev-btn').forEach(b => {
        b.classList.remove('selected-high', 'selected-medium', 'selected-low', 'selected-critical');
    });
    
    // Add appropriate selected class
    const classMap = {
        'low': 'selected-low',
        'medium': 'selected-medium',
        'high': 'selected-high',
        'critical': 'selected-critical'
    };
    btn.classList.add(classMap[severity]);
    
    // Store selected severity
    selectedSeverity = severity;
}

function updateSafetyTips(type) {
    const tips = SAFETY_TIPS[type] || SAFETY_TIPS.other;
    const container = document.getElementById('safety-tips');
    
    let html = '<ul style="list-style:none;padding:0;margin:0;">';
    tips.forEach(tip => {
        html += `<li style="display:flex;gap:8px;margin-bottom:10px;font-size:13px;color:#4a5568;">
            <i class="fa-solid fa-check-circle" style="color:#34c759;margin-top:2px;"></i>
            <span>${tip}</span>
        </li>`;
    });
    html += '</ul>';
    
    container.innerHTML = html;
}

async function submitReport() {
    const description = document.getElementById('description').value.trim();
    const reporterName = document.getElementById('reporter-name').value.trim();
    const reporterPhone = document.getElementById('reporter-phone').value.trim();
    
    // Validation
    if (!selectedType) {
        showToast('Please select an emergency type', 'error');
        return;
    }
    
    if (!description) {
        showToast('Please describe the situation', 'error');
        return;
    }
    
    // Disable submit button
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    
    try {
        const response = await fetch(`${API}/report/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF
            },
            body: JSON.stringify({
                emergency_type: selectedType,
                severity: selectedSeverity,
                description: description,
                reporter_name: reporterName,
                reporter_phone: reporterPhone,
                latitude: userLatitude,
                longitude: userLongitude
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show success state
            document.getElementById('form-card').style.display = 'none';
            document.getElementById('success-state').style.display = 'block';
            document.getElementById('success-report-id').textContent = `Report ID: ${data.report_id}`;
            
            // Start live tracking
            startLiveTracking(data.report_id);
            
            showToast('Emergency reported successfully. Help is on the way!', 'success');
        } else {
            throw new Error(data.error || 'Failed to submit report');
        }
    } catch (error) {
        console.error('Error submitting report:', error);
        showToast('Failed to submit report. Please try again.', 'error');
        
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Emergency Report';
    }
}

function startLiveTracking(reportId) {
    const tracker = document.getElementById('live-tracker');
    
    // Initial status check
    checkReportStatus(reportId);
    
    // Poll for updates every 5 seconds
    const interval = setInterval(async () => {
        const status = await checkReportStatus(reportId);
        
        // Stop polling if resolved
        if (status && status.status === 'resolved') {
            clearInterval(interval);
        }
    }, 5000);
}

async function checkReportStatus(reportId) {
    try {
        const response = await fetch(`${API}/status/${reportId}/`);
        const data = await response.json();
        
        const tracker = document.getElementById('live-tracker');
        
        let statusHtml = `
            <div style="background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;margin-top:16px;">
                <div style="font-size:12px;color:#718096;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">
                    Current Status
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                    <span class="status-badge status-${data.status}">${data.status_display}</span>
                </div>
        `;
        
        if (data.timeline && data.timeline.length > 0) {
            statusHtml += `
                <div style="font-size:12px;color:#718096;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.5px;">
                    Timeline
                </div>
                <div style="display:flex;flex-direction:column;gap:8px;">
            `;
            
            data.timeline.slice(-3).forEach(entry => {
                statusHtml += `
                    <div style="display:flex;gap:8px;font-size:12px;color:#4a5568;">
                        <i class="fa-solid fa-circle" style="font-size:6px;margin-top:5px;color:#718096;"></i>
                        <span>${entry.note}</span>
                    </div>
                `;
            });
            
            statusHtml += '</div>';
        }
        
        statusHtml += '</div>';
        tracker.innerHTML = statusHtml;
        
        return data;
    } catch (error) {
        console.error('Error checking status:', error);
        return null;
    }
}

function resetForm() {
    // Reset all form fields
    document.getElementById('description').value = '';
    document.getElementById('reporter-name').value = '';
    document.getElementById('reporter-phone').value = '';
    
    // Reset selections
    selectedType = null;
    selectedSeverity = 'high';
    
    // Remove selected classes
    document.querySelectorAll('.type-btn').forEach(b => b.classList.remove('selected'));
    document.querySelectorAll('.sev-btn').forEach(b => {
        b.classList.remove('selected-high', 'selected-medium', 'selected-low', 'selected-critical');
    });
    
    // Reset severity to default high
    document.querySelector('[data-sev="high"]').classList.add('selected-high');
    
    // Hide extended form
    document.getElementById('form-extended').style.display = 'none';
    
    // Show form card, hide success state
    document.getElementById('form-card').style.display = 'block';
    document.getElementById('success-state').style.display = 'none';
    
    // Reset safety tips
    document.getElementById('safety-tips').innerHTML = `
        <div style="color:#4a5568;font-size:13px;text-align:center;padding:12px 0;">
            <i class="fa-solid fa-circle-info" style="font-size:20px;margin-bottom:8px;display:block;"></i>
            Select an emergency type to see relevant safety tips.
        </div>
    `;
    
    // Re-enable submit button
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Send Emergency Report';
}

function triggerSOS() {
    if (confirm('SOS: This will immediately alert all emergency response units. Continue?')) {
        // Submit as critical emergency with type 'other'
        selectedType = 'other';
        selectedSeverity = 'critical';
        document.getElementById('description').value = 'SOS - Immediate assistance required';
        submitReport();
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// GPS location detection
if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userLatitude = position.coords.latitude.toFixed(6);
            userLongitude = position.coords.longitude.toFixed(6);
            document.getElementById('gps-text-main').textContent = `Location detected: ${userLatitude}, ${userLongitude}`;
            document.getElementById('gps-status-text').textContent = 'Accuracy: ±' + Math.round(position.coords.accuracy) + 'm';
            document.getElementById('gps-spinner').style.display = 'none';
        },
        (error) => {
            document.getElementById('gps-text-main').textContent = 'Location unavailable';
            document.getElementById('gps-status-text').textContent = 'Please enable GPS for accurate response';
            document.getElementById('gps-spinner').style.display = 'none';
        },
        { timeout: 10000, enableHighAccuracy: true }
    );
} else {
    document.getElementById('gps-text-main').textContent = 'GPS not supported';
    document.getElementById('gps-status-text').textContent = 'Please report your location manually';
    document.getElementById('gps-spinner').style.display = 'none';
}
