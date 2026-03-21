with open('frontend/templates/login.html', 'r') as f:
    lines = f.readlines()

# Find the position to add script (before the last {% endblock %})
for i in range(len(lines)-1, -1, -1):
    if '{% endblock %}' in lines[i] and i > 0 and '{% block scripts %}' not in lines[i-1]:
        # Insert script before this line
        script = '''
{% block scripts %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Show logout success message
    if (urlParams.get('logout') === 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.innerHTML = \`
            <i class="fas fa-check-circle"></i> 
            <strong>Success!</strong> You have been logged out successfully.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        \`;
        
        const container = document.querySelector('.container.mt-4') || 
                         document.querySelector('.row.justify-content-center') ||
                         document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
        
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
    
    // Show login required message
    if (urlParams.get('login') === 'required') {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-warning alert-dismissible fade show';
        alertDiv.innerHTML = \`
            <i class="fas fa-exclamation-triangle"></i> 
            <strong>Please Login:</strong> You need to login to access that page.
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        \`;
        
        const container = document.querySelector('.container.mt-4') || 
                         document.querySelector('.row.justify-content-center') ||
                         document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
        
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }
});
</script>
{% endblock %}
'''
        lines.insert(i, script)
        break

with open('frontend/templates/login.html', 'w') as f:
    f.writelines(lines)

print("Added message handling to login.html")
