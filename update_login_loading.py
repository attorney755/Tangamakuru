import re

with open('frontend/templates/login.html', 'r') as f:
    content = f.read()

# Find the login form submit handler
if 'document.getElementById(\'loginForm\')' in content:
    # Replace the existing submit handler
    new_handler = '''
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const remember = document.getElementById('remember') ? document.getElementById('remember').checked : false;
        
        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Logging in...';
        submitBtn.disabled = true;
        
        // Show loading message
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'alert alert-info alert-dismissible fade show mt-3';
        loadingMsg.innerHTML = \`
            <i class="fas fa-spinner fa-spin"></i> 
            <strong>Authenticating...</strong> Please wait while we verify your credentials.
        \`;
        this.parentNode.insertBefore(loadingMsg, this.nextSibling);
        
        // Wait 2 seconds before making API call (for better UX)
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                    remember: remember
                })
            });
            
            const data = await response.json();
            
            // Remove loading message
            loadingMsg.remove();
            
            if (response.ok) {
                // Save token and user data
                localStorage.setItem('tangamakuru_token', data.token);
                localStorage.setItem('tangamakuru_user', JSON.stringify(data.user));
                
                // Show success message
                const successMsg = document.createElement('div');
                successMsg.className = 'alert alert-success alert-dismissible fade show mt-3';
                successMsg.innerHTML = \`
                    <i class="fas fa-check-circle"></i> 
                    <strong>Login successful!</strong> Welcome back, \${data.user.first_name}.
                    <p class="mb-0 small">Redirecting to your dashboard...</p>
                \`;
                this.parentNode.insertBefore(successMsg, this.nextSibling);
                
                // Redirect based on role
                setTimeout(() => {
                    if (data.user.role === 'admin') {
                        window.location.href = '/admin/dashboard';
                    } else if (data.user.role === 'officer') {
                        window.location.href = '/officer/dashboard';
                    } else {
                        window.location.href = '/dashboard';
                    }
                }, 2000);
            } else {
                // Show error message
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                
                const errorMsg = document.createElement('div');
                errorMsg.className = 'alert alert-danger alert-dismissible fade show mt-3';
                errorMsg.innerHTML = \`
                    <i class="fas fa-exclamation-triangle"></i> 
                    <strong>Login failed:</strong> \${data.error}
                \`;
                this.parentNode.insertBefore(errorMsg, this.nextSibling);
                
                // Auto-remove error after 5 seconds
                setTimeout(() => {
                    if (errorMsg.parentNode) {
                        errorMsg.remove();
                    }
                }, 5000);
            }
        } catch (error) {
            // Remove loading message
            loadingMsg.remove();
            
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
            
            const errorMsg = document.createElement('div');
            errorMsg.className = 'alert alert-danger alert-dismissible fade show mt-3';
            errorMsg.innerHTML = \`
                <i class="fas fa-exclamation-triangle"></i> 
                <strong>Network error:</strong> \${error.message}
            \`;
            this.parentNode.insertBefore(errorMsg, this.nextSibling);
        }
    });
    '''
    
    # Replace the existing submit handler
    pattern = r'document\.getElementById\(["\']loginForm["\']\)\.addEventListener\(["\']submit["\'].*?catch.*?\n.*?\n.*?\n'
    content = re.sub(pattern, new_handler, content, flags=re.DOTALL)
    
    with open('frontend/templates/login.html', 'w') as f:
        f.write(content)
    
    print("Updated login form with loading message")
else:
    print("Could not find login form in login.html")
