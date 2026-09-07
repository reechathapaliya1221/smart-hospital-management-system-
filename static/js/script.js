// Smart Hospital Queue System - Enhanced JavaScript

// Auto-refresh function
let autoRefreshInterval = null;

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Start auto-refresh for queue status (30 seconds)
    startAutoRefresh(30000);
    
    // Add loading animation to forms
    addFormLoadingAnimation();
    
    // Initialize real-time WebSocket connection
    initWebSocket();
    
    // Add smooth scrolling
    addSmoothScrolling();
});

// Auto-refresh function
function startAutoRefresh(interval) {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    autoRefreshInterval = setInterval(function() {
        refreshData();
    }, interval);
}

// Refresh data
function refreshData() {
    if (window.location.pathname === '/queue-status/') {
        showToast('Refreshing queue data...', 'info');
        location.reload();
    }
}

// Form loading animation
function addFormLoadingAnimation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.disabled = true;
                
                // Re-enable after 3 seconds (or on error)
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 3000);
            }
        });
    });
}

// WebSocket connection for real-time updates
function initWebSocket() {
    // Check if WebSocket is supported
    if (!window.WebSocket) {
        console.log('WebSocket not supported');
        return;
    }
    
    const wsScheme = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsScheme}//${window.location.host}/ws/queue/`;
    
    try {
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = function(e) {
            console.log('WebSocket connected');
            updateConnectionStatus('connected');
        };
        
        socket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            handleRealTimeUpdate(data);
        };
        
        socket.onerror = function(e) {
            console.log('WebSocket error:', e);
            updateConnectionStatus('error');
        };
        
        socket.onclose = function(e) {
            console.log('WebSocket closed');
            updateConnectionStatus('disconnected');
            // Attempt to reconnect after 5 seconds
            setTimeout(initWebSocket, 5000);
        };
    } catch(e) {
        console.log('WebSocket connection failed:', e);
    }
}

// Handle real-time updates
function handleRealTimeUpdate(data) {
    if (data.type === 'queue_update') {
        // Update waiting counts without full reload
        const waitingElement = document.getElementById('total-waiting');
        if (waitingElement && data.data.waiting_count !== undefined) {
            waitingElement.textContent = data.data.waiting_count;
            waitingElement.classList.add('highlight');
            setTimeout(() => waitingElement.classList.remove('highlight'), 500);
        }
        
        showToast('Queue updated!', 'success');
    }
}

// Update connection status
function updateConnectionStatus(status) {
    const statusElement = document.getElementById('connection-status');
    if (statusElement) {
        statusElement.className = `connection-status ${status}`;
        statusElement.title = `WebSocket ${status}`;
    }
}

// Smooth scrolling
function addSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast-modern');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.className = 'toast-modern';
    toast.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="flex-shrink-0">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} fa-2x" 
                   style="color: ${type === 'success' ? '#06d6a0' : type === 'error' ? '#ef233c' : '#4361ee'}"></i>
            </div>
            <div class="flex-grow-1 ms-3">
                ${message}
            </div>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast && toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// Print ticket
function printTicket() {
    window.print();
}

// Download QR code
function downloadQR() {
    const qrImg = document.querySelector('#qr-code-img');
    if (qrImg) {
        const link = document.createElement('a');
        link.download = 'hospital-token-qr.png';
        link.href = qrImg.src;
        link.click();
        showToast('QR code downloaded!', 'success');
    } else {
        showToast('QR code not found', 'error');
    }
}

// Copy token to clipboard
function copyToken(tokenNumber) {
    navigator.clipboard.writeText(tokenNumber).then(() => {
        showToast('Token copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy token', 'error');
    });
}

// Search filter for tables
function filterTable(inputId, tableId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    input.addEventListener('keyup', function() {
        const filter = this.value.toLowerCase();
        const table = document.getElementById(tableId);
        const rows = table.getElementsByTagName('tr');
        
        for (let i = 1; i < rows.length; i++) {
            const row = rows[i];
            let text = '';
            const cells = row.getElementsByTagName('td');
            
            for (let j = 0; j < cells.length; j++) {
                text += cells[j].textContent.toLowerCase();
            }
            
            row.style.display = text.includes(filter) ? '' : 'none';
        }
    });
}

// Refresh specific section
function refreshSection(sectionId, url) {
    fetch(url)
        .then(response => response.text())
        .then(html => {
            const section = document.getElementById(sectionId);
            if (section) {
                section.innerHTML = html;
                showToast('Section refreshed!', 'success');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('Failed to refresh', 'error');
        });
}

// Countdown timer for estimated wait time
function startCountdown(elementId, minutes) {
    let time = minutes * 60;
    const element = document.getElementById(elementId);
    
    if (!element) return;
    
    const interval = setInterval(() => {
        if (time <= 0) {
            clearInterval(interval);
            element.innerHTML = 'Ready now!';
            showToast('Your token is ready!', 'success');
        } else {
            const mins = Math.floor(time / 60);
            const secs = time % 60;
            element.innerHTML = `${mins}:${secs.toString().padStart(2, '0')}`;
            time--;
        }
    }, 1000);
}

// Add highlight animation to elements
function addHighlightAnimation(element) {
    if (element) {
        element.classList.add('highlight');
        setTimeout(() => {
            element.classList.remove('highlight');
        }, 500);
    }
}

// Export data as CSV
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Data exported successfully!', 'success');
}

function convertToCSV(data) {
    const headers = Object.keys(data[0]);
    const csvRows = [];
    csvRows.push(headers.join(','));
    
    for (const row of data) {
        const values = headers.map(header => {
            const val = row[header];
            return `"${String(val).replace(/"/g, '""')}"`;
        });
        csvRows.push(values.join(','));
    }
    
    return csvRows.join('\n');
}

// Dark mode toggle
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark);
    showToast(`${isDark ? 'Dark' : 'Light'} mode enabled`, 'info');
}

// Check for saved dark mode preference
if (localStorage.getItem('darkMode') === 'true') {
    document.body.classList.add('dark-mode');
}