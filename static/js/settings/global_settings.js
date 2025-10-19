// ==================== Admin Functions - Global Settings ====================
// This file handles global settings management for administrators

/**
 * Save global settings
 * @param {Event} event - The form submission event
 * @param {boolean} force - Whether to force save without confirmation
 */
window.saveGlobalSettings = async function(event, force = false) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form).entries());

    // Explicitly handle checkboxes to ensure they are sent even when false
    data.CALIBRE_ADD_DUPLICATES = form.querySelector('#CALIBRE_ADD_DUPLICATES').checked;
    data.DISABLE_NORMAL_USER_UPLOAD = form.querySelector('#DISABLE_NORMAL_USER_UPLOAD').checked;
    data.REQUIRE_INVITE_CODE = form.querySelector('#REQUIRE_INVITE_CODE').checked;
    data.ENABLE_ACTIVITY_LOG = form.querySelector('#ENABLE_ACTIVITY_LOG').checked;


    if (force) {
        data._force_update = true;
    }

    const response = await fetch('/api/global_settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (response.ok && result.require_confirmation) {
        if (confirm(result.warning)) {
            // 用户确认，强制保存
            await window.saveGlobalSettings(event, true);
        }
    } else {
        alert(result.message || result.error);
        if (response.ok) {
            location.reload();
        }
    }
}

/**
 * Clean up all audiobook files
 */
window.cleanupAllAudiobooks = async function() {
    if (!confirm(t.confirmCleanup)) {
        return;
    }

    try {
        const response = await fetch('/api/admin/cleanup_audiobooks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
        });
        const result = await response.json();
        
        if (response.ok) {
            alert(result.message);
            window.location.href = '/';
        } else {
            alert(`${t.cleanupFailed}: ${result.error}`);
        }
    } catch (error) {
        alert(`${t.anErrorOccurred}: ${error.message}`);
    }
}

/**
 * Test SMTP settings by sending a test email
 */
window.testSmtpSettings = async function() {
    const form = document.getElementById('globalSettingsForm');
    const data = {
        SMTP_SERVER: form.SMTP_SERVER.value,
        SMTP_PORT: form.SMTP_PORT.value,
        SMTP_USERNAME: form.SMTP_USERNAME.value,
        SMTP_PASSWORD: form.SMTP_PASSWORD.value,
        SMTP_ENCRYPTION: form.SMTP_ENCRYPTION.value,
        to_address: form.test_email_address.value
    };

    if (!data.to_address) {
        alert(t.enterTestEmail);
        return;
    }

    const response = await fetch('/api/test_smtp', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await response.json();
    alert(result.message || result.error);
}