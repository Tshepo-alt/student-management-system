// frontend/js/api.js
// API Configuration
const API_BASE_URL = '';  // Empty string uses relative path (same origin)

/**
 * Make API calls with authentication
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
 * @param {string} endpoint - API endpoint
 * @param {object} data - Request body (for POST/PUT)
 * @returns {Promise} - Fetch response
 */
async function apiCall(method = 'GET', endpoint, data = null) {
    const options = {
        method: method,
        headers: {
            'Accept': 'application/json'
        }
    };

    // Add authorization token if user is logged in (JWT)
    const token = localStorage.getItem('access_token');
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    // Add Content-Type for non-file uploads
    if (!(data instanceof FormData)) {
        options.headers['Content-Type'] = 'application/json';
    }

    // Add body for POST/PUT requests
    if (data && (method === 'POST' || method === 'PUT')) {
        if (data instanceof FormData) {
            options.body = data;
        } else {
            options.body = JSON.stringify(data);
        }
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
        
        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            console.warn('401 Unauthorized - Session expired or invalid token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('isLoggedIn');
            localStorage.removeItem('user_role');
            localStorage.removeItem('user_id');
            localStorage.removeItem('user_email');
            localStorage.removeItem('user_name');
            
            // Clear any intervals
            if (window.refreshInterval) {
                clearInterval(window.refreshInterval);
                window.refreshInterval = null;
            }
            
            // Don't redirect if we're already on login page
            if (!window.location.pathname.includes('login.html')) {
                window.location.href = '/pages/login.html';
            }
            throw new Error('Session expired. Please login again.');
        }
        
        // Handle other error responses
        if (!response.ok && response.status !== 401) {
            console.error(`API Error: ${response.status} ${response.statusText} - ${endpoint}`);
        }
        
        return response;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

/**
 * Safe API call that doesn't redirect on errors (for admin dashboard)
 * @param {string} endpoint - API endpoint
 * @param {object} options - Fetch options
 * @returns {Promise} - Response or null on error
 */
async function safeApiCall(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        console.log('No token found, cannot make API call');
        return null;
    }
    
    try {
        const response = await fetch(endpoint, {
            ...options,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        // ONLY redirect on 401 (unauthorized)
        if (response.status === 401) {
            console.warn('Token expired, redirecting to login...');
            localStorage.clear();
            if (!window.location.pathname.includes('login.html')) {
                window.location.href = '/pages/login.html';
            }
            return null;
        }
        
        return response;
    } catch (error) {
        console.error(`API call error to ${endpoint}:`, error);
        return null;
    }
}

/**
 * Handle file uploads
 * @param {string} endpoint - API endpoint
 * @param {File} file - File to upload
 * @returns {Promise} - Fetch response
 */
async function uploadFile(endpoint, file) {
    const formData = new FormData();
    formData.append('file', file);

    const options = {
        method: 'POST',
        headers: {}
    };

    const token = localStorage.getItem('access_token');
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: options.headers,
            body: formData
        });

        if (response.status === 401) {
            console.warn('Upload - 401 Unauthorized');
            localStorage.clear();
            if (!window.location.pathname.includes('login.html')) {
                window.location.href = '/pages/login.html';
            }
        }

        return response;
    } catch (error) {
        console.error('Upload Error:', error);
        throw error;
    }
}

/**
 * Format date to readable format
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    try {
        return new Date(dateString).toLocaleDateString(undefined, options);
    } catch (e) {
        return dateString;
    }
}

/**
 * Format date with time
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date and time
 */
function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
    try {
        return new Date(dateString).toLocaleDateString(undefined, options);
    } catch (e) {
        return dateString;
    }
}

/**
 * Format currency
 * @param {number} amount - Amount to format
 * @param {string} currency - Currency code (default: BWP)
 * @returns {string} - Formatted currency
 */
function formatCurrency(amount, currency = 'BWP') {
    if (amount === undefined || amount === null) return 'P 0.00';
    return new Intl.NumberFormat('en-BW', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
function isAuthenticated() {
    const token = localStorage.getItem('access_token');
    const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true';
    return token !== null && isLoggedIn;
}

/**
 * Get current user
 * @returns {object} - User object
 */
function getCurrentUser() {
    const user = localStorage.getItem('user');
    if (user) {
        try {
            return JSON.parse(user);
        } catch (e) {
            console.error('Error parsing user data:', e);
            return null;
        }
    }
    return null;
}

/**
 * Get current user role
 * @returns {string} - User role (student, staff, admin, etc.)
 */
function getUserRole() {
    const user = getCurrentUser();
    const roleFromStorage = localStorage.getItem('user_role');
    return user ? user.role : (roleFromStorage || null);
}

/**
 * Get user name
 * @returns {string} - User's display name
 */
function getUserName() {
    const user = getCurrentUser();
    const nameFromStorage = localStorage.getItem('user_name');
    if (user && user.first_name) {
        return `${user.first_name} ${user.last_name || ''}`.trim();
    }
    return nameFromStorage || user?.username || 'User';
}

/**
 * Logout user
 */
async function logout() {
    try {
        // Try to call logout endpoint
        await apiCall('POST', '/api/auth/logout');
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear all localStorage items
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        localStorage.removeItem('isLoggedIn');
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_email');
        localStorage.removeItem('user_name');
        
        // Clear any intervals
        if (window.refreshInterval) {
            clearInterval(window.refreshInterval);
            window.refreshInterval = null;
        }
        
        // Redirect to home page
        window.location.href = '/index.html';
    }
}

/**
 * Refresh JWT token
 */
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            console.log('Token refreshed successfully');
            return true;
        } else if (response.status === 401) {
            console.warn('Refresh token expired, logging out...');
            await logout();
            return false;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
    }
    
    return false;
}

/**
 * Auto-refresh token periodically
 */
let refreshInterval = null;

function startTokenRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    
    // Refresh every 50 minutes (tokens expire in 60 minutes)
    refreshInterval = setInterval(async () => {
        if (isAuthenticated()) {
            const success = await refreshToken();
            if (!success) {
                console.log('Token refresh failed, logging out...');
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
                logout();
            }
        } else {
            // Stop refreshing if not authenticated
            if (refreshInterval) {
                clearInterval(refreshInterval);
                refreshInterval = null;
            }
        }
    }, 50 * 60 * 1000);
}

/**
 * Stop token refresh
 */
function stopTokenRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

/**
 * Check if user has admin role
 * @returns {boolean}
 */
function isAdmin() {
    const role = getUserRole();
    return role === 'admin' || role === 'administrator';
}

/**
 * Check if user has staff role
 * @returns {boolean}
 */
function isStaff() {
    const role = getUserRole();
    return role === 'staff' || role === 'lecturer' || role === 'finance';
}

/**
 * Show loading spinner
 * @param {string} elementId - Element to show spinner in
 */
function showLoading(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="loading-spinner"></div><p>Loading...</p>';
    }
}

/**
 * Hide loading spinner and show content
 * @param {string} elementId - Element to update
 * @param {string} content - HTML content to display
 */
function hideLoading(elementId, content) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = content;
    }
}

/**
 * Show error message
 * @param {string} message - Error message to display
 * @param {string} elementId - Element to show error in
 */
function showError(message, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="error-message">⚠️ ${message}</div>`;
        setTimeout(() => {
            if (element.innerHTML === `<div class="error-message">⚠️ ${message}</div>`) {
                element.innerHTML = '';
            }
        }, 5000);
    } else {
        alert(`Error: ${message}`);
    }
}

/**
 * Show success message
 * @param {string} message - Success message to display
 * @param {string} elementId - Element to show success in
 */
function showSuccess(message, elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `<div class="success-message">✅ ${message}</div>`;
        setTimeout(() => {
            if (element.innerHTML === `<div class="success-message">✅ ${message}</div>`) {
                element.innerHTML = '';
            }
        }, 3000);
    } else {
        alert(message);
    }
}

// Initialize token refresh if user is logged in
if (isAuthenticated()) {
    startTokenRefresh();
}

// Export functions for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        apiCall,
        safeApiCall,
        uploadFile,
        formatDate,
        formatDateTime,
        formatCurrency,
        isAuthenticated,
        getCurrentUser,
        getUserRole,
        getUserName,
        logout,
        refreshToken,
        startTokenRefresh,
        stopTokenRefresh,
        isAdmin,
        isStaff,
        showLoading,
        hideLoading,
        showError,
        showSuccess
    };
}