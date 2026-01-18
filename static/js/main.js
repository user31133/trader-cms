// HTMX Configuration
htmx.config.defaultIndicatorStyle = "class";
htmx.config.refreshOnHistoryMiss = true;

// Close modal on successful form submission
document.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.xhr.status === 200 || evt.detail.xhr.status === 201) {
        const modal = document.querySelector('.modal.show');
        if (modal) {
            bootstrap.Modal.getInstance(modal).hide();
        }
    }
});

// Handle form errors
document.addEventListener('htmx:responseError', function(evt) {
    console.error('Request failed:', evt.detail);
    alert('An error occurred. Please try again.');
});

// Close modal on escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            bootstrap.Modal.getInstance(modal).hide();
        });
    }
});

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Confirm deletion
function confirmDelete(url) {
    if (confirm('Are you sure you want to delete this item?')) {
        htmx.ajax('DELETE', url, { target: 'closest tr', swap: 'outerHTML swap:1s' });
    }
    return false;
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Mobile sidebar toggle
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('show');
}

// Debounce function for search
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

// Handle visibility toggle
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('visibility-toggle')) {
        const value = e.target.checked;
        const data = { visibility: value };

        htmx.ajax('PATCH', e.target.getAttribute('hx-patch'), {
            values: data
        });
    }
});

// Confirm before leaving page with unsaved changes
let hasUnsavedChanges = false;

document.addEventListener('change', function(e) {
    if (e.target.closest('form')) {
        hasUnsavedChanges = true;
    }
});

document.addEventListener('submit', function(e) {
    hasUnsavedChanges = false;
});

window.addEventListener('beforeunload', function(e) {
    if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = '';
    }
});

// Initialize tooltips if Bootstrap is available
document.addEventListener('DOMContentLoaded', function() {
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
});

// Handle HTMX modal swaps
document.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'edit-modal' && evt.detail.xhr.status === 200) {
        const modal = new bootstrap.Modal(document.getElementById('edit-modal'));
        modal.show();
    }
});

// Log HTMX events in development
if (process.env.NODE_ENV === 'development') {
    htmx.logAll();
}
