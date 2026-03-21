// Main JavaScript for TANGAMAKURU

// Global variables for form handling
let addressSearchTimeout;
let uploadedFiles = [];

// API Base URL
const API_BASE = 'http://localhost:5000';
// ... rest of the code continues ...

function checkAuth() {
    const token = localStorage.getItem('tangamakuru_token');
    const user = localStorage.getItem('tangamakuru_user');
    
    if (!token || !user) {
        // Redirect to login if not on login page
        if (!window.location.pathname.includes('/login') && 
            !window.location.pathname.includes('/register')) {
            window.location.href = '/login';
        }
        return null;
    }
    
    return {
        token: token,
        user: JSON.parse(user)
    };
}

// Add logout function
function logout() {
    localStorage.removeItem('tangamakuru_token');
    localStorage.removeItem('tangamakuru_user');
    window.location.href = '/login';
}

// Add click handler for logout button
document.addEventListener('DOMContentLoaded', function() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
});

// Add this to main.js
function checkAuth() {
    const token = localStorage.getItem('tangamakuru_token');
    const user = localStorage.getItem('tangamakuru_user');
    
    // If no token but we're on a protected page (not login/register/logout)
    if (!token && !user) {
        const allowedPages = ['/login', '/register', '/logout', '/'];
        const currentPath = window.location.pathname;
        
        if (!allowedPages.includes(currentPath)) {
            window.location.href = '/login?login=required';
            return false;
        }
    }
    
    return true;
}

// Run check on page load
document.addEventListener('DOMContentLoaded', checkAuth);

// Make authenticated API requests
async function apiRequest(endpoint, options = {}) {
    const auth = checkAuth();
    if (!auth && endpoint !== '/auth/login' && endpoint !== '/auth/register') {
        return null;
    }
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(auth ? { 'Authorization': `Bearer ${auth.token}` } : {})
        }
    };
    
    const response = await fetch(API_BASE + endpoint, {
        ...defaultOptions,
        ...options
    });
    
    if (response.status === 401) {
        // Token expired, redirect to login
        localStorage.removeItem('tangamakuru_token');
        localStorage.removeItem('tangamakuru_user');
        window.location.href = '/login';
        return null;
    }
    
    return response;
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-RW', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Format status badge
function getStatusBadge(status) {
    const statusMap = {
        'pending': { class: 'status-pending', text: 'PENDING' },
        'in_progress': { class: 'status-in_progress', text: 'IN PROGRESS' },
        'resolved': { class: 'status-resolved', text: 'RESOLVED' },
        'cancelled': { class: 'status-cancelled', text: 'CANCELLED' }
    };
    
    const statusInfo = statusMap[status] || { class: 'status-pending', text: status.toUpperCase() };
    return `<span class="status-badge ${statusInfo.class}">${statusInfo.text}</span>`;
}

// Format priority badge
function getPriorityBadge(priority) {
    const priorityMap = {
        'low': { class: 'priority-low', text: 'LOW' },
        'medium': { class: 'priority-medium', text: 'MEDIUM' },
        'high': { class: 'priority-high', text: 'HIGH' },
        'urgent': { class: 'priority-urgent', text: 'URGENT' }
    };
    
    const priorityInfo = priorityMap[priority] || { class: 'priority-medium', text: priority.toUpperCase() };
    return `<span class="priority-badge ${priorityInfo.class}">${priorityInfo.text}</span>`;
}

// Logout function
function logout() {
    localStorage.removeItem('tangamakuru_token');
    localStorage.removeItem('tangamakuru_user');
    window.location.href = '/login';
}

// Export functions for use in other files
window.Tangamakuru = {
    checkAuth,
    apiRequest,
    formatDate,
    getStatusBadge,
    getPriorityBadge,
    logout
};