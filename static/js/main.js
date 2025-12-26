/**
 * ifinsure - Main JavaScript
 * Minimal vanilla JS for essential interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.3s ease';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        // Show toggle on mobile
        if (window.innerWidth <= 768) {
            sidebarToggle.style.display = 'inline-flex';
        }
        
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('open');
                }
            }
        });
        
        // Handle resize
        window.addEventListener('resize', function() {
            if (window.innerWidth <= 768) {
                sidebarToggle.style.display = 'inline-flex';
            } else {
                sidebarToggle.style.display = 'none';
                sidebar.classList.remove('open');
            }
        });
    }
    
    // Dropdown toggles
    const dropdowns = document.querySelectorAll('.dropdown');
    dropdowns.forEach(function(dropdown) {
        const trigger = dropdown.querySelector('.dropdown-trigger');
        if (trigger) {
            trigger.addEventListener('click', function(e) {
                e.stopPropagation();
                dropdown.classList.toggle('open');
            });
        }
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function() {
        dropdowns.forEach(function(dropdown) {
            dropdown.classList.remove('open');
        });
    });
    
    // Form validation styling
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function() {
            const inputs = form.querySelectorAll('.form-input, .form-select');
            inputs.forEach(function(input) {
                if (input.required && !input.value) {
                    input.classList.add('error');
                } else {
                    input.classList.remove('error');
                }
            });
        });
    });
    
    // Confirm dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(function(element) {
        element.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // Number formatting for currency inputs
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value && this.step === '0.01') {
                this.value = parseFloat(this.value).toFixed(2);
            }
        });
    });
});
