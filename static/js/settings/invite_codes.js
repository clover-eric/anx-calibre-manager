// ==================== Invite Code Management (Admin Only) ====================
// This file handles invite code management functionality for administrators

/**
 * Load and display all invite codes
 */
async function loadInviteCodes() {
    if (!isAdmin) return;
    
    try {
        const response = await fetch('/api/admin/invite-codes');
        if (response.ok) {
            const codes = await response.json();
            const tbody = document.querySelector('#inviteCodeTable tbody');
            if (!tbody) return;
            
            tbody.innerHTML = '';
            codes.forEach(code => {
                const row = document.createElement('tr');
                const statusText = code.is_active ? t.active : t.disabled;
                const expiresAt = code.expires_at ? formatLocalTime(code.expires_at) : t.neverExpires;
                const createdAt = formatLocalTime(code.created_at);
                
                row.innerHTML = `
                    <td><code>${code.code}</code></td>
                    <td>${code.max_uses}</td>
                    <td>${code.current_uses}</td>
                    <td>${code.created_by || t.unknown}</td>
                    <td>${createdAt}</td>
                    <td>${expiresAt}</td>
                    <td>${statusText}</td>
                    <td>
                        <button class="button-small" onclick="toggleInviteCode(${code.id})">${code.is_active ? t.disable : t.enable}</button>
                        <button class="button-small button-danger" onclick="deleteInviteCode(${code.id})">${t.delete}</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading invite codes:', error);
    }
}

/**
 * Generate a new invite code
 * @param {Event} event - The form submission event
 */
window.generateInviteCode = async function(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = {
        action: 'create',
        custom_code: formData.get('custom_code') || '',
        max_uses: formData.get('max_uses'),
        expires_hours: formData.get('expires_hours') || null
    };
    
    try {
        const response = await fetch('/api/admin/invite-codes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        if (response.ok && result.success) {
            alert(t.generateInviteSuccess.replace('{code}', result.code));
            await loadInviteCodes();
            event.target.reset();
        } else {
            alert(t.generateInviteFailed.replace('{error}', result.error || t.unknownError));
        }
    } catch (error) {
        alert(t.generateInviteError);
    }
}

/**
 * Toggle (enable/disable) an invite code
 * @param {number} codeId - The ID of the invite code to toggle
 */
window.toggleInviteCode = async function(codeId) {
    try {
        const response = await fetch('/api/admin/invite-codes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'toggle', code_id: codeId })
        });
        
        if (response.ok) {
            await loadInviteCodes();
        } else {
            const error = await response.json();
            alert(t.operationFailedWithError.replace('{error}', error.error || t.unknownError));
        }
    } catch (error) {
        alert(t.operationFailed);
    }
}

/**
 * Delete an invite code
 * @param {number} codeId - The ID of the invite code to delete
 */
window.deleteInviteCode = async function(codeId) {
    if (!confirm(t.confirmDeleteInvite)) return;
    
    try {
        const response = await fetch('/api/admin/invite-codes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'delete', code_id: codeId })
        });
        
        if (response.ok) {
            await loadInviteCodes();
        } else {
            const error = await response.json();
            alert(t.deleteFailedWithError.replace('{error}', error.error || t.unknownError));
        }
    } catch (error) {
        alert(t.deleteFailed);
    }
}