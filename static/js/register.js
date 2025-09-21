document.addEventListener('DOMContentLoaded', function() {
    // --- Translatable Strings ---
    const t = {
        passwordMismatch: _('Password confirmation does not match'),
        passwordTooShort: _('Password must be at least 6 characters'),
        invalidUsername: _('Username can only contain letters, numbers and underscores, 3-50 characters long'),
        registrationSuccess: _('Registration successful! Please login.'),
        registrationFailed: _('Registration failed'),
        networkError: _('Network error, please try again later')
    };

    const registerForm = document.getElementById('registerForm');
    const errorMessage = document.getElementById('error-message');
    
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(registerForm);
        const password = formData.get('password');
        const confirmPassword = formData.get('confirm_password');
        
        // 客户端验证
        if (password !== confirmPassword) {
            errorMessage.textContent = t.passwordMismatch;
            return;
        }
        
        if (password.length < 6) {
            errorMessage.textContent = t.passwordTooShort;
            return;
        }
        
        const username = formData.get('username');
        if (!/^[a-zA-Z0-9_]{3,50}$/.test(username)) {
            errorMessage.textContent = t.invalidUsername;
            return;
        }
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    invite_code: formData.get('invite_code'),
                    username: username,
                    password: password,
                    language: formData.get('language')
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                // 显示成功提示
                alert(data.message || t.registrationSuccess);
                window.location.href = data.redirect_url || '/login';
            } else {
                errorMessage.textContent = data.error || t.registrationFailed;
            }
        } catch (error) {
            errorMessage.textContent = t.networkError;
        }
    });
    
    // 实时密码确认验证
    const confirmPasswordField = document.getElementById('confirm_password');
    const passwordField = document.getElementById('password');
    
    confirmPasswordField.addEventListener('input', function() {
        if (passwordField.value && confirmPasswordField.value) {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity(t.passwordMismatch);
            } else {
                confirmPasswordField.setCustomValidity('');
            }
        }
    });
    
    passwordField.addEventListener('input', function() {
        if (confirmPasswordField.value) {
            if (passwordField.value !== confirmPasswordField.value) {
                confirmPasswordField.setCustomValidity(t.passwordMismatch);
            } else {
                confirmPasswordField.setCustomValidity('');
            }
        }
    });
});
