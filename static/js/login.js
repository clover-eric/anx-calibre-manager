document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const form = e.target;
    const passwordInput = document.getElementById('password');
    const errorMessageDiv = document.getElementById('error-message');
    
    // If password was disabled for 2FA, re-enable it just for submission
    const wasPasswordDisabled = passwordInput.disabled;
    if (wasPasswordDisabled) {
        passwordInput.disabled = false;
    }

    const formData = new FormData(form);

    // Re-disable it right after creating FormData to maintain UI state
    if (wasPasswordDisabled) {
        passwordInput.disabled = true;
    }

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData,
        });
        const result = await response.json();
        errorMessageDiv.textContent = '';

        if (result.require_2fa) {
            document.getElementById('otp-group').style.display = 'block';
            document.getElementById('otp_code').required = true;
            passwordInput.disabled = true; // Disable for user interaction
        } else if (result.success) {
            window.location.href = result.redirect_url;
        } else if (result.error) {
            errorMessageDiv.textContent = result.error;
            passwordInput.disabled = false; // Re-enable on error
        }
    } catch (error) {
        errorMessageDiv.textContent = '发生网络错误，请重试。';
        passwordInput.disabled = false; // Re-enable on network error
    }
});