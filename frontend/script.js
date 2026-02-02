// ========================================
// Enterprise Knowledge Intelligence - Frontend
// ========================================

// ✅ UPDATED Backend URL (your Render deployment)
const API_BASE = 'https://mini-rag-mm0h.onrender.com';

// State
let uploadRole = 'Employee';
let searchRole = 'Employee';
let selectedFile = null;

// DOM Elements
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
    
    toast.innerHTML = `${icon}<div class="toast-message">${message}</div>`;
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
    uploadZone.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files[0]);
    });
    
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
    
    uploadBtn.addEventListener('click', handleUpload);
}

function handleFileSelect(file) {
    if (!file) return;
    
    if (file.type !== 'application/pdf') {
        showToast('Please select a PDF file', 'error');
        return;
    }
    
    if (file.size > 20 * 1024 * 1024) {
        showToast('File exceeds 20MB limit', 'error');
        return;
    }
    
    selectedFile = file;
    
    const uploadText = uploadZone.querySelector('.upload-text');
    const uploadSubtext = uploadZone.querySelector('.upload-subtext');
    uploadText.textContent = file.name;
    uploadSubtext.textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    
    showToast(`Selected: ${file.name}`, 'success');
}

async function handleUpload() {
    if (!selectedFile) {
        showToast('Please select a PDF first', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('role', uploadRole);
    formData.append('doc_type', docTypeSelect.value);
    
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
            showToast('Upload successful!', 'success');
            displayUploadResult(data);
            
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
        showToast(error.message || 'Upload failed', 'error');
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
                <div>🔒 Access: ${data.doc_type}</div>
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
            
            const siblings = chip.parentElement.querySelectorAll('.chip');
            siblings.forEach(s => s.classList.remove('active'));
            chip.classList.add('active');
            
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
    
    loadingState.style.display = 'block';
    answerContainer.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
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
        showToast(error.message || 'Search failed', 'error');
        loadingState.style.display = 'none';
    }
}

function displayAnswer(data) {
    loadingState.style.display = 'none';
    answerContainer.style.display = 'block';
    
    answerText.textContent = data.answer;
    
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
        sourcesList.innerHTML = '<div style="color: var(--text-tertiary); font-size: 0.875rem;">No sources</div>';
    }
    
    answerContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ========================================
// BACKEND HEALTH CHECK
// ========================================

async function checkBackendHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        
        if (response.ok) {
            console.log('✅ Backend healthy');
        } else {
            console.warn('⚠️ Backend health check failed');
        }
    } catch (error) {
        console.error('❌ Cannot connect to backend:', error);
        showToast('Backend connection issue', 'error');
    }
}

// ========================================
// ERROR HANDLERS
// ========================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('An error occurred', 'error');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Promise rejection:', event.reason);
    showToast('An error occurred', 'error');
});
