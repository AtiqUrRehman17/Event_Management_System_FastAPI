/* ============================================
   EventHub - Main JavaScript
   Handles: Auth, API calls, Alerts, Navigation
   ============================================ */

// ── Constants ───────────────────────────────

const API_BASE = '/api/v1';

// ── Token Management ────────────────────────

function getToken() {
    return localStorage.getItem('access_token');
}

function getRefreshToken() {
    return localStorage.getItem('refresh_token');
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem('user') || 'null');
    } catch {
        return null;
    }
}

function clearAuth() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
}

// ── API Call Helper ─────────────────────────

async function apiCall(url, options = {}) {
    const token = getToken();

    const defaultHeaders = {
        'Content-Type': 'application/json',
    };

    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    const config = {
        method: options.method || 'GET',
        headers: { ...defaultHeaders, ...options.headers },
    };

    if (options.body) {
        config.body = options.body;
    }

    try {
        const response = await fetch(url, config);

        // Handle 401 - try refresh token
        if (response.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                // Retry with new token
                config.headers['Authorization'] = `Bearer ${getToken()}`;
                const retryResponse = await fetch(url, config);
                return await retryResponse.json();
            } else {
                clearAuth();
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    window.location.href = '/login';
                }
                return { success: false, message: 'Session expired. Please login again.' };
            }
        }

        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        return { success: false, message: 'Network error. Please try again.' };
    }
}

// ── Token Refresh ───────────────────────────

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                localStorage.setItem('access_token', data.data.access_token);
                localStorage.setItem('refresh_token', data.data.refresh_token);
                return true;
            }
        }
        return false;
    } catch {
        return false;
    }
}

// ── Auth Status Check ───────────────────────

function checkAuthStatus() {
    const token = getToken();
    const user = getUser();

    const loginNav = document.getElementById('loginNav');
    const registerNav = document.getElementById('registerNav');
    const userDropdown = document.getElementById('userDropdown');
    const navUsername = document.getElementById('navUsername');
    const adminLink = document.getElementById('adminLink');

    if (token && user) {
        // Logged in
        if (loginNav) loginNav.classList.add('d-none');
        if (registerNav) registerNav.classList.add('d-none');
        if (userDropdown) userDropdown.classList.remove('d-none');
        if (navUsername) navUsername.textContent = user.first_name || user.username;

        // Show admin link for admins
        if (adminLink && user.role === 'admin') {
            adminLink.classList.remove('d-none');
        }
    } else {
        // Not logged in
        if (loginNav) loginNav.classList.remove('d-none');
        if (registerNav) registerNav.classList.remove('d-none');
        if (userDropdown) userDropdown.classList.add('d-none');
    }
}

// ── Logout ──────────────────────────────────

async function logout() {
    const token = getToken();
    const refreshToken = getRefreshToken();

    try {
        if (token) {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    refresh_token: refreshToken
                })
            });
        }
    } catch (e) {
        console.error('Logout error:', e);
    }

    clearAuth();
    showAlert('Logged out successfully.', 'success');
    setTimeout(() => {
        window.location.href = '/login';
    }, 500);
}

// ── Alert System ────────────────────────────

function showAlert(message, type = 'info', duration = 4000) {
    const container = document.getElementById('alertContainer');
    if (!container) return;

    const alertId = 'alert-' + Date.now();

    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show" id="${alertId}" role="alert">
            <div class="d-flex align-items-center">
                <i class="fas ${getAlertIcon(type)} me-2"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    container.insertAdjacentHTML('afterbegin', alertHtml);

    // Auto dismiss
    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 300);
            }
        }, duration);
    }
}

function getAlertIcon(type) {
    const icons = {
        'success': 'fa-check-circle',
        'danger': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle'
    };
    return icons[type] || 'fa-info-circle';
}

// ── Date Formatting ─────────────────────────

function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        return date.toLocaleDateString('en-US', options);
    } catch {
        return dateString;
    }
}

function formatDateShort(dateString) {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        const options = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        return date.toLocaleDateString('en-US', options);
    } catch {
        return dateString;
    }
}

function formatDateRelative(dateString) {
    if (!dateString) return 'N/A';

    try {
        const date = new Date(dateString);
        const now = new Date();
        const diff = date - now;
        const days = Math.ceil(diff / (1000 * 60 * 60 * 24));

        if (days < 0) return `${Math.abs(days)} days ago`;
        if (days === 0) return 'Today';
        if (days === 1) return 'Tomorrow';
        if (days <= 7) return `In ${days} days`;
        if (days <= 30) return `In ${Math.ceil(days / 7)} weeks`;
        return formatDateShort(dateString);
    } catch {
        return dateString;
    }
}

// ── Number Formatting ───────────────────────

function formatCurrency(amount) {
    if (amount === null || amount === undefined) return '$0.00';
    return '$' + parseFloat(amount).toFixed(2);
}

function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}

// ── URL Helpers ─────────────────────────────

function getUrlParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

function setUrlParam(name, value) {
    const url = new URL(window.location);
    if (value) {
        url.searchParams.set(name, value);
    } else {
        url.searchParams.delete(name);
    }
    window.history.replaceState({}, '', url);
}

// ── Debounce Helper ─────────────────────────

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ── Loading State Helpers ───────────────────

function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="text-muted mt-2">Loading...</p>
            </div>
        `;
    }
}

function showEmpty(containerId, message = 'No data found', icon = 'fa-inbox') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fas ${icon} fa-4x text-muted mb-3"></i>
                <h5 class="text-muted">${message}</h5>
            </div>
        `;
    }
}

function showError(containerId, message = 'Something went wrong') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-exclamation-circle fa-4x text-danger mb-3"></i>
                <h5 class="text-muted">${message}</h5>
                <button class="btn btn-outline-primary mt-2" onclick="location.reload()">
                    <i class="fas fa-redo me-1"></i>Try Again
                </button>
            </div>
        `;
    }
}

// ── Confirm Dialog ──────────────────────────

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// ── Copy to Clipboard ───────────────────────

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard!', 'success', 2000);
    }).catch(() => {
        showAlert('Failed to copy.', 'danger', 2000);
    });
}

// ── Active Nav Link ─────────────────────────

function setActiveNavLink() {
    const path = window.location.pathname;
    document.querySelectorAll('.navbar .nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === path || (href !== '/' && path.startsWith(href))) {
            link.classList.add('active');
        }
    });
}

// ── Initialize on Page Load ─────────────────

document.addEventListener('DOMContentLoaded', function () {
    setActiveNavLink();
});