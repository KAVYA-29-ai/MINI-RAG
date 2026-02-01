// ========================================
// GOD LEVEL JAVASCRIPT - API Integration
// ========================================

// 🔗 Backend API URL (UPDATE THIS AFTER RAILWAY DEPLOYMENT)
const API_BASE = 'https://your-backend.up.railway.app'; // TODO: Update this!

// State
let uploadRole = 'Employee';
let searchRole = 'Employee';
let selectedFile = null;

// ========================================
// DOM ELEMENTS
// ========================================

const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const uploadBtn = document.getElementById('uploadBtn');
const uploadResult = document.getElementById('uploadResult');
const docTypeSelect = document.getElementById('docType');

const queryInput = document.getElementById('queryInput');
const searchBtn = document.getElementById('searchBtn');
const loadingState = document.getElementById('loadingState');
const answerContainer = document.getElementById('answerContainer');
const answerText = document.getElementById('answerText');
const sourcesList = document.getElementById('sourcesList');

// ========================================
// INITIALIZATION
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initializeUploadZone();
    initializeRoleButtons();
    initializeSearch();
    checkBackendHealth();
});

// ========================================
// TOAST NOTIFICATIONS
// ========================================

function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' 
        ? '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    
    toast.innerHTML = `
        ${icon}
        <div class="toast-message">${message}</div>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========================================
// UPLOAD ZONE
// ========================================

function initializeUploadZone() {
    // Click to upload
    uploadZone.addEventListener('click', () => fileInput.click());
    
    // File selected
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });
    
    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFileSelect(e.dataTransfer.files[0]);
    });
    
    // Upload button
    uploadBtn.addEventListener('click', handleUpload);
}

function handleFileSelect(file) {
    if (!file) return;
    
    // Validate file type
    if (file.type !== 'application/pdf') {
        showToast('Please select a PDF file', 'error');
        return;
    }
    
    // Validate file size (20MB)
    if (file.size > 20 * 1024 * 1024) {
        showToast('File size exceeds 20MB limit', 'error');
        return;
    }
    
    selectedFile = file;
    
    // Update UI
    const uploadText = uploadZone.querySelector('.upload-text');
    const uploadSubtext = uploadZone.querySelector('.upload-subtext');
    uploadText.textContent = file.name;
    uploadSubtext.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    
    showToast(`Selected: ${file.name}`, 'success');
}

async function handleUpload() {
    if (!selectedFile) {
        showToast('Please select a PDF file first', 'error');
        return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('role', uploadRole);
    formData.append('doc_type', docTypeSelect.value);
    
    // Show loading state
    uploadBtn.disabled = true;
    uploadBtn.classList.add('loading');
    uploadResult.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Document uploaded successfully!', 'success');
            displayUploadResult(data);
            
            // Reset upload zone
            setTimeout(() => {
                selectedFile = null;
                const uploadText = uploadZone.querySelector('.upload-text');
                const uploadSubtext = uploadZone.querySelector('.upload-subtext');
                uploadText.textContent = 'Drag & drop PDF here';
                uploadSubtext.textContent = 'or click to browse';
                fileInput.value = '';
            }, 2000);
        } else {
            throw new Error(data.detail || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast(error.message || 'Upload failed. Please try again.', 'error');
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.classList.remove('loading');
    }
}

function displayUploadResult(data) {
    uploadResult.innerHTML = `
        <div style="margin-top: 1rem; padding: 1rem; background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px;">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                <svg style="width: 20px; height: 20px; stroke: #10b981;" viewBox="0 0 24 24" fill="none" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span style="font-weight: 600; color: #10b981;">Upload Successful</span>
            </div>
            <div style="font-size: 0.875rem; color: var(--text-secondary);">
                <div>📄 <strong>${data.filename}</strong></div>
                <div>📊 ${data.chunks_created} chunks created</div>
                <div>🔒 Access level: ${data.doc_type}</div>
            </div>
        </div>
    `;
}

// ========================================
// ROLE SELECTION
// ========================================

function initializeRoleButtons() {
    const roleChips = document.querySelectorAll('.chip');
    
    roleChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const role = chip.dataset.role;
            const target = chip.dataset.target || 'upload';
            
            // Update active state
            const siblings = chip.parentElement.querySelectorAll('.chip');
            siblings.forEach(s => s.classList.remove('active'));
            chip.classList.add('active');
            
            // Update role
            if (target === 'search') {
                searchRole = role;
            } else {
                uploadRole = role;
            }
        });
    });
}

// ========================================
// SEARCH
// ========================================

function initializeSearch() {
    searchBtn.addEventListener('click', handleSearch);
    
    queryInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSearch();
        }
    });
}

async function handleSearch() {
    const query = queryInput.value.trim();
    
    if (!query) {
        showToast('Please enter a question', 'error');
        return;
    }
    
    // Show loading
    loadingState.style.display = 'block';
    answerContainer.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                role: searchRole
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayAnswer(data);
        } else {
            throw new Error(data.detail || 'Search failed');
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast(error.message || 'Search failed. Please try again.', 'error');
        loadingState.style.display = 'none';
    }
}

function displayAnswer(data) {
    loadingState.style.display = 'none';
    answerContainer.style.display = 'block';
    
    // Display answer
    answerText.textContent = data.answer;
    
    // Display sources
    if (data.sources && data.sources.length > 0) {
        sourcesList.innerHTML = data.sources.map(source => `
            <div class="source-item">
                <div>
                    <span class="source-name">📄 ${source.filename}</span>
                    ${source.page ? `<span class="source-page"> · Page ${source.page}</span>` : ''}
                </div>
                <span class="source-similarity">${(source.similarity * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    } else {
        sourcesList.innerHTML = '<div style="color: var(--text-tertiary); font-size: 0.875rem;">No sources available</div>';
    }
    
    // Scroll to answer
    answerContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ========================================
// BACKEND HEALTH CHECK
// ========================================

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`, {
            method: 'GET'
        });
        
        if (response.ok) {
            console.log('✅ Backend is healthy');
        } else {
            console.warn('⚠️ Backend health check failed');
        }
    } catch (error) {
        console.error('❌ Cannot connect to backend:', error);
        showToast('Warning: Backend connection issue. Check API_BASE in script.js', 'error');
    }
}

// ========================================
// UPLOAD RESULT DISPLAY
// ========================================

function displayUploadResult(data) {
    uploadResult.style.display = 'block';
    uploadResult.innerHTML = `
        <div class="result-success">
            <svg class="result-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            <div class="result-content">
                <div class="result-title">Upload Successful!</div>
                <div class="result-details">
                    <div>📄 ${data.filename}</div>
                    <div>📊 ${data.chunks_created} chunks created</div>
                    <div>📝 ${data.text_length} characters processed</div>
                    <div>🔒 ${data.doc_type} access level</div>
                </div>
            </div>
        </div>
    `;
}

// ========================================
// UTILITY FUNCTIONS
// ========================================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ========================================
// ERROR BOUNDARY
// ========================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('An unexpected error occurred', 'error');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred', 'error');
});