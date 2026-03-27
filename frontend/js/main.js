/**
 * Main JavaScript file for University Student Portal
 * Handles common functionality across all pages
 */

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeLogout();
});

/**
 * Initialize navigation based on login status
 */
function initializeNavigation() {
    // Check for JWT token instead of isLoggedIn flag
    const token = localStorage.getItem('access_token');
    const isLoggedIn = token !== null;
    const user = getCurrentUser();

    if (isLoggedIn && user) {
        // Update navigation for logged-in users
        const loginLink = document.getElementById('loginLink');
        const registerLink = document.getElementById('registerLink');
        const profileLink = document.getElementById('profileLink');
        const logoutLink = document.getElementById('logoutLink');
        const heroLogin = document.getElementById('heroLogin');
        const heroRegister = document.getElementById('heroRegister');

        if (loginLink) loginLink.style.display = 'none';
        if (registerLink) registerLink.style.display = 'none';
        if (profileLink) {
            profileLink.style.display = 'block';
            profileLink.href = 'pages/student-dashboard.html';
        }
        if (logoutLink) logoutLink.style.display = 'block';
        if (heroLogin) heroLogin.style.display = 'none';
        if (heroRegister) heroRegister.style.display = 'none';
    } else {
        // Show login/register for non-logged-in users
        const loginLink = document.getElementById('loginLink');
        const registerLink = document.getElementById('registerLink');
        const profileLink = document.getElementById('profileLink');
        const logoutLink = document.getElementById('logoutLink');

        if (loginLink) loginLink.style.display = 'block';
        if (registerLink) registerLink.style.display = 'block';
        if (profileLink) profileLink.style.display = 'none';
        if (logoutLink) logoutLink.style.display = 'none';
    }
}

/**
 * Initialize logout functionality
 */
function initializeLogout() {
    const logoutLinks = document.querySelectorAll('#logoutLink');
    
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                logout();
            }
        });
    });
}

/**
 * Get current user from localStorage
 * @returns {object|null}
 */
function getCurrentUser() {
    const user = localStorage.getItem('user');
    if (user) {
        try {
            return JSON.parse(user);
        } catch (e) {
            return null;
        }
    }
    return null;
}

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
function isAuthenticated() {
    const token = localStorage.getItem('access_token');
    return token !== null;
}

/**
 * Logout user
 */
async function logout() {
    const token = localStorage.getItem('access_token');
    
    try {
        // Try to call logout endpoint if token exists
        if (token) {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    // Clear all localStorage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_role');
    
    // Redirect to home or login
    window.location.href = '/';
}

/**
 * Validate email format
 * @param {string} email - Email to validate
 * @returns {boolean}
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate password strength
 * @param {string} password - Password to validate
 * @returns {object} - {valid: boolean, message: string}
 */
function validatePassword(password) {
    if (password.length < 8) {
        return { valid: false, message: 'Password must be at least 8 characters' };
    }
    if (!/[A-Z]/.test(password)) {
        return { valid: false, message: 'Password must contain at least one uppercase letter' };
    }
    if (!/[0-9]/.test(password)) {
        return { valid: false, message: 'Password must contain at least one number' };
    }
    return { valid: true, message: 'Password is valid' };
}

/**
 * Show notification
 * @param {string} message - Message to display
 * @param {string} type - Type of notification (success, error, info, warning)
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background-color: ${getNotificationColor(type)};
        color: white;
        border-radius: 4px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 9999;
        animation: slideIn 0.3s ease-in-out;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in-out';
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

/**
 * Get notification color based on type
 * @param {string} type - Type of notification
 * @returns {string} - Color code
 */
function getNotificationColor(type) {
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    return colors[type] || colors.info;
}

/**
 * Add CSS animations
 */
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

/**
 * Debounce function for search and input handlers
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function}
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function for scroll and resize handlers
 * @param {function} func - Function to throttle
 * @param {number} limit - Throttle limit in milliseconds
 * @returns {function}
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Format file size
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Validate file type
 * @param {File} file - File to validate
 * @param {array} allowedTypes - Allowed MIME types
 * @returns {boolean}
 */
function validateFileType(file, allowedTypes) {
    return allowedTypes.includes(file.type);
}

/**
 * Validate file size
 * @param {File} file - File to validate
 * @param {number} maxSize - Max size in MB
 * @returns {boolean}
 */
function validateFileSize(file, maxSize) {
    return file.size <= (maxSize * 1024 * 1024);
}

/**
 * Copy to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise}
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success');
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

/**
 * Generate unique ID
 * @returns {string}
 */
function generateId() {
    return '_' + Math.random().toString(36).substr(2, 9);
}

/**
 * Parse query parameters from URL
 * @returns {object}
 */
function getQueryParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    const pairs = queryString.split('&');
    
    pairs.forEach(pair => {
        const [key, value] = pair.split('=');
        params[decodeURIComponent(key)] = decodeURIComponent(value || '');
    });
    
    return params;
}

/**
 * Redirect to page with parameters
 * @param {string} page - Page URL
 * @param {object} params - Query parameters
 */
function redirectWith(page, params) {
    const queryString = new URLSearchParams(params).toString();
    window.location.href = page + (queryString ? '?' + queryString : '');
}

/**
 * Check if element is in viewport
 * @param {Element} element - Element to check
 * @returns {boolean}
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Smooth scroll to element
 * @param {string} elementId - Element ID to scroll to
 */
function smoothScroll(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

/**
 * Local storage with expiration
 */
const StorageWithExpiration = {
    set: function(key, value, expirationMinutes) {
        const item = {
            value: value,
            expiration: expirationMinutes ? Date.now() + (expirationMinutes * 60 * 1000) : null
        };
        localStorage.setItem(key, JSON.stringify(item));
    },
    
    get: function(key) {
        const item = JSON.parse(localStorage.getItem(key));
        if (!item) return null;
        
        if (item.expiration && Date.now() > item.expiration) {
            localStorage.removeItem(key);
            return null;
        }
        
        return item.value;
    }
};

// Export functions if using modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        validateEmail,
        validatePassword,
        showNotification,
        debounce,
        throttle,
        formatFileSize,
        validateFileType,
        validateFileSize,
        copyToClipboard,
        generateId,
        getQueryParams,
        redirectWith,
        isInViewport,
        smoothScroll,
        StorageWithExpiration,
        getCurrentUser,
        isAuthenticated,
        logout
    };
}