with open('frontend/templates/login.html', 'r') as f:
    lines = f.readlines()

# Find a good place to insert message display (after card-header)
for i, line in enumerate(lines):
    if 'card-body' in line and 'p-4' in line:
        # Insert message container after this line
        message_html = '''
                <!-- Message Display Area -->
                <div id="pageMessages" class="mb-3"></div>
        '''
        lines.insert(i + 1, message_html)
        break

# Add script to handle URL messages
script_added = False
for i, line in enumerate(lines):
    if '{% block scripts %}' in line:
        # Add message handling script
        message_script = '''
<script>
document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const messageDiv = document.getElementById('pageMessages');
    
    // Show logout success message
    if (urlParams.get('logout') === 'success') {
        const message = urlParams.get('message') || 'You have been successfully logged out.';
        
        messageDiv.innerHTML = \`
            <div class="alert alert-success alert-dismissible fade show">
                <i class="fas fa-check-circle"></i> 
                <strong>Success!</strong> \${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        \`;
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (messageDiv.firstChild) {
                messageDiv.firstChild.remove();
            }
        }, 4000);
        
        // Clean URL
        window.history.replaceState({}, document.title, '/login');
    }
    
    // Show login required message
    if (urlParams.get('login') === 'required') {
        messageDiv.innerHTML = \`
            <div class="alert alert-warning alert-dismissible fade show">
                <i class="fas fa-exclamation-triangle"></i> 
                <strong>Authentication Required</strong>
                <p class="mb-0 small">Please login to access that page.</p>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        \`;
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            if (messageDiv.firstChild) {
                messageDiv.firstChild.remove();
            }
        }, 4000);
        
        // Clean URL
        window.history.replaceState({}, document.title, '/login');
    }
});
</script>
'''
        lines.insert(i + 1, message_script)
        script_added = True
        break

if not script_added:
    # Add scripts block at the end
    lines.append('''
{% block scripts %}
<script>
// Same script as above...
</script>
{% endblock %}
''')

with open('frontend/templates/login.html', 'w') as f:
    f.writelines(lines)

print("Added message display to login page")
