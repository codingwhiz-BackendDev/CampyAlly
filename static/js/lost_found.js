// Lost & Found System JavaScript
const API = '/parking/api/lost-found';
const CSRF = '{{ csrf_token }}';

let uploadedImages = [];

// Toggle category-specific fields
function toggleCategoryFields() {
    const category = document.getElementById('category').value;
    const personFields = document.getElementById('person-fields');
    const itemFields = document.getElementById('item-fields');
    const titleLabel = document.getElementById('title-label');
    
    // Hide all conditional fields first
    personFields.style.display = 'none';
    itemFields.style.display = 'none';
    
    // Show relevant fields based on category
    if (category === 'lost_person' || category === 'found_person') {
        personFields.style.display = 'block';
        titleLabel.textContent = 'Person Name *';
    } else if (category === 'lost_item' || category === 'found_item') {
        itemFields.style.display = 'block';
        titleLabel.textContent = 'Item Title *';
    } else {
        titleLabel.textContent = 'Title / Name *';
    }
}

// Image upload handling
const imageDropZone = document.getElementById('image-drop-zone');
const imageInput = document.getElementById('image-input');

imageDropZone.addEventListener('click', () => imageInput.click());

imageDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    imageDropZone.style.borderColor = 'rgba(16, 185, 129, 0.5)';
    imageDropZone.style.background = 'rgba(16, 185, 129, 0.05)';
});

imageDropZone.addEventListener('dragleave', () => {
    imageDropZone.style.borderColor = 'rgba(0, 0, 0, 0.15)';
    imageDropZone.style.background = 'rgba(255, 255, 255, 0.5)';
});

imageDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    imageDropZone.style.borderColor = 'rgba(0, 0, 0, 0.15)';
    imageDropZone.style.background = 'rgba(255, 255, 255, 0.5)';
    
    const files = e.dataTransfer.files;
    handleFiles(files);
});

function handleImageUpload(event) {
    const files = event.target.files;
    handleFiles(files);
}

function handleFiles(files) {
    for (let file of files) {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                uploadedImages.push({
                    file: file,
                    dataUrl: e.target.result
                });
                updateImagePreview();
            };
            reader.readAsDataURL(file);
        }
    }
}

function updateImagePreview() {
    const previewContainer = document.getElementById('image-preview');
    previewContainer.innerHTML = '';
    
    uploadedImages.forEach((img, index) => {
        const div = document.createElement('div');
        div.className = 'image-preview-item';
        div.innerHTML = `
            <img src="${img.dataUrl}" alt="Preview">
            <button type="button" class="remove-btn" onclick="removeImage(${index})">
                <i class="fa-solid fa-times"></i>
            </button>
        `;
        previewContainer.appendChild(div);
    });
}

function removeImage(index) {
    uploadedImages.splice(index, 1);
    updateImagePreview();
}

// Camera capture
function openCamera() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.capture = 'environment';
    input.onchange = (e) => handleImageUpload(e);
    input.click();
}

// Form submission
document.getElementById('lf-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector('.submit-btn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
    
    const formData = new FormData();
    
    // Common fields
    formData.append('category', document.getElementById('category').value);
    formData.append('title', document.getElementById('title').value);
    formData.append('description', document.getElementById('description').value);
    formData.append('location', document.getElementById('location').value);
    formData.append('phone_number', document.getElementById('phone_number').value);
    formData.append('urgency', document.getElementById('urgency').value);
    
    const dateTime = document.getElementById('date_time').value;
    if (dateTime) {
        formData.append('date_time', dateTime);
    }
    
    // Reporter info
    formData.append('reporter_name', document.getElementById('reporter_name').value);
    formData.append('reporter_email', document.getElementById('reporter_email').value);
    
    // Person-specific fields
    const age = document.getElementById('age').value;
    const gender = document.getElementById('gender').value;
    if (age) formData.append('age', age);
    if (gender) formData.append('gender', gender);
    
    // Item-specific fields
    const itemType = document.getElementById('item_type').value;
    if (itemType) formData.append('item_type', itemType);
    
    // Images
    uploadedImages.forEach(img => {
        formData.append('image', img.file);
    });
    
    // GPS location
    if (userLatitude && userLongitude) {
        formData.append('latitude', userLatitude);
        formData.append('longitude', userLongitude);
    }
    
    try {
        const response = await fetch(`${API}/submit/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('Report submitted successfully!', 'success');
            resetForm();
            // Refresh the page to show new report
            setTimeout(() => window.location.reload(), 1500);
        } else {
            throw new Error(data.error || 'Failed to submit report');
        }
    } catch (error) {
        console.error('Error submitting report:', error);
        showToast('Failed to submit report. Please try again.', 'error');
    }
    
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Submit Report';
});

function resetForm() {
    document.getElementById('lf-form').reset();
    uploadedImages = [];
    updateImagePreview();
    toggleCategoryFields();
}

// Filter reports
function filterReports() {
    const categoryFilter = document.getElementById('category-filter').value;
    const statusFilter = document.getElementById('status-filter').value;
    const searchQuery = document.getElementById('search-input').value.toLowerCase();
    
    const cards = document.querySelectorAll('.report-card');
    
    cards.forEach(card => {
        const cardCategory = card.dataset.category;
        const cardStatus = card.dataset.status;
        const cardTitle = card.querySelector('h3').textContent.toLowerCase();
        const cardDescription = card.querySelector('.report-description').textContent.toLowerCase();
        
        let visible = true;
        
        if (categoryFilter && cardCategory !== categoryFilter) {
            visible = false;
        }
        
        if (statusFilter && cardStatus !== statusFilter) {
            visible = false;
        }
        
        if (searchQuery && !cardTitle.includes(searchQuery) && !cardDescription.includes(searchQuery)) {
            visible = false;
        }
        
        card.style.display = visible ? 'block' : 'none';
    });
}

// Show contact info
function showContact(phoneNumber) {
    showToast(`Contact: ${phoneNumber}`, 'success');
}

// Toast notification
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-xmark' : 'fa-circle-info'}"></i>
        <span>${message}</span>
    `;
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 3500);
}

// GPS location detection
let userLatitude = null;
let userLongitude = null;

if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
        (position) => {
            userLatitude = position.coords.latitude;
            userLongitude = position.coords.longitude;
        },
        (error) => {
            console.log('Location unavailable');
        },
        { timeout: 10000, enableHighAccuracy: true }
    );
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Set default date/time to now
    const now = new Date();
    const dateTimeInput = document.getElementById('date_time');
    dateTimeInput.value = now.toISOString().slice(0, 16);
});
