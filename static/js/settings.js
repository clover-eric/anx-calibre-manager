const isAdmin = JSON.parse(document.getElementById('is-admin-data').textContent);

// --- Tab Control ---
window.openTab = function(evt, tabName) {
    let i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].classList.remove('active', 'visible');
    }
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].classList.remove('active');
    }
    
    const activeTab = document.getElementById(tabName);
    activeTab.classList.add('active');
    evt.currentTarget.classList.add('active');

    setTimeout(() => {
        activeTab.classList.add('visible');
    }, 10);
}

// --- User Settings Logic ---
async function populateForms() {
    const userRes = await fetch('/api/user_settings');
    const userData = await userRes.json();
    document.getElementById('kindle_email').value = userData.kindle_email || '';
    document.getElementById('send_format_priority').value = (userData.send_format_priority || []).join(', ');
    document.getElementById('theme').value = userData.theme || 'auto';
    document.getElementById('force_epub_conversion').checked = userData.force_epub_conversion;
    document.getElementById('stats_enabled').checked = userData.stats_enabled;
    document.getElementById('stats_public').checked = userData.stats_public;

    const statsEnabledCheckbox = document.getElementById('stats_enabled');
    const statsUrlContainer = document.getElementById('stats_url_container');
    const statsUrlLink = document.getElementById('stats_url');

    function toggleStatsUrl() {
        if (statsEnabledCheckbox.checked) {
            const url = `${window.location.origin}/stats/${userData.username}`;
            statsUrlLink.href = url;
            statsUrlLink.textContent = url;
            statsUrlContainer.style.display = 'block';
        } else {
            statsUrlContainer.style.display = 'none';
        }
    }

    statsEnabledCheckbox.addEventListener('change', toggleStatsUrl);
    toggleStatsUrl(); // Initial check

    if (userData.smtp_from_address) {
        const tipElement = document.getElementById('smtp_from_address_tip');
        tipElement.textContent = _('Please make sure to add the sender email address ({email}) to your Amazon Kindle trusted email list.').replace('{email}', userData.smtp_from_address);
    }
    update2FAStatus(userData.has_2fa);
    
    if (isAdmin) {
        const globalRes = await fetch('/api/global_settings');
        const globalData = await globalRes.json();
        for (const key in globalData) {
            const el = document.getElementById(key);
            if (el) {
                if (el.type === 'checkbox') {
                    el.checked = globalData[key];
                } else {
                    el.value = globalData[key];
                }
            }
        }
        await fetchUsers();
    }
    await fetchMcpTokens();

    // Setup Koreader WebDAV URL
    const koreaderWebDavUrlElement = document.getElementById('koreader-webdav-url');
    if (koreaderWebDavUrlElement) {
        const webdavUrl = `${window.location.origin}/webdav/${userData.username}/`;
        koreaderWebDavUrlElement.textContent = webdavUrl;
        koreaderWebDavUrlElement.addEventListener('click', () => {
            navigator.clipboard.writeText(webdavUrl).then(() => {
                alert(_('WebDAV address copied to clipboard'));
            }, () => {
                alert(_('Copy failed'));
            });
        });
    }

    document.getElementById('settings-loading-overlay').style.display = 'none';
    document.getElementById('userSettings').classList.add('visible');
}

function update2FAStatus(is_enabled) {
    const statusContainer = document.getElementById('2fa_status_container');
    if (is_enabled) {
        statusContainer.innerHTML = `<p>${_('2FA has been enabled.')}</p><button type="button" class="button-danger" onclick="disable2FA()">${_('Disable')}</button>`;
    } else {
        statusContainer.innerHTML = `<p>${_('2FA is not enabled.')}</p><button type="button" class="button" onclick="setup2FA()">${_('Enable')}</button>`;
    }
}

window.setup2FA = async function() {
    const response = await fetch('/api/2fa/setup', { method: 'POST' });
    const data = await response.json();
    if (response.ok) {
        document.getElementById('2fa_status_container').style.display = 'none';
        document.getElementById('2fa_setup_container').style.display = 'block';
        document.getElementById('otp_secret_key').textContent = data.secret;
        document.getElementById('qr_code_container').innerHTML = `<img src="${data.qr_code}" alt="QR Code">`;
    } else {
        alert(data.error);
    }
}

window.cancel2FASetup = function() {
    document.getElementById('2fa_status_container').style.display = 'block';
    document.getElementById('2fa_setup_container').style.display = 'none';
}

window.verify2FA = async function() {
    const otp_code = document.getElementById('otp_code').value;
    const response = await fetch('/api/2fa/verify', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ otp_code: otp_code })
    });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        cancel2FASetup();
        update2FAStatus(true);
    }
}

window.disable2FA = async function() {
    if (!confirm(_('Are you sure you want to disable 2FA?'))) return;
    const response = await fetch('/api/2fa/disable', { method: 'POST' });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        update2FAStatus(false);
    }
}

window.saveUserSettings = async function(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());
    data.force_epub_conversion = formData.has('force_epub_conversion');
    data.stats_enabled = formData.has('stats_enabled');
    data.stats_public = formData.has('stats_public');
    const response = await fetch('/api/user_settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        localStorage.setItem('theme', data.theme);
        (function() {
            const theme = localStorage.getItem('theme') || 'auto';
            if (theme === 'dark') {
                document.documentElement.classList.add('dark-mode');
            } else if (theme === 'light') {
                document.documentElement.classList.remove('dark-mode');
            } else { 
                if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.documentElement.classList.add('dark-mode');
                } else {
                    document.documentElement.classList.remove('dark-mode');
                }
            }
        })();
    }
}

// --- MCP Token Logic ---
async function fetchMcpTokens() {
    const response = await fetch('/api/mcp_tokens');
    const tokens = await response.json();
    const listEl = document.getElementById('mcp-token-list');
    listEl.innerHTML = '';
    if (tokens.length === 0) {
        listEl.innerHTML = `<p>${_('No available tokens.')}</p>`;
    } else {
        tokens.forEach(token => {
            const item = document.createElement('div');
            item.className = 'token-item';
            item.innerHTML = `
                <div>
                    <span class="token-value">${token.token}</span>
                    <small style="display: block; color: #666;">${_('Created at')}: ${new Date(token.created_at).toLocaleString()}</small>
                </div>
                <button class="button-danger button-small" onclick="deleteMcpToken(${token.id})">${_('Delete')}</button>
            `;
            listEl.appendChild(item);
        });
    }
}

window.generateMcpToken = async function() {
    const response = await fetch('/api/mcp_tokens', { method: 'POST' });
    const result = await response.json();
    if (response.ok) {
        alert(_('New token has been generated.'));
        await fetchMcpTokens();
    } else {
        alert(result.error || 'Failed to generate token.');
    }
}

window.deleteMcpToken = async function(tokenId) {
    if (!confirm(_('Are you sure you want to delete this token?'))) return;
    const response = await fetch(`/api/mcp_tokens/${tokenId}`, { method: 'DELETE' });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        await fetchMcpTokens();
    }
}

// --- Admin Functions ---
window.saveGlobalSettings = async function(event) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form).entries());
    const response = await fetch('/api/global_settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        location.reload();
    }
}

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
        alert(_('Please enter a test recipient email address.'));
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

async function fetchUsers() {
    const response = await fetch('/api/users');
    const users = await response.json();
    const tbody = document.querySelector('#userTable tbody');
    tbody.innerHTML = '';
    users.forEach(user => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${user.id}</td>
            <td>${user.username}</td>
            <td>${user.role}</td>
            <td>
                <button class="button-small" onclick="editUser(${user.id}, '${user.username}', '${user.role}')">${_('Edit')}</button>
                <button class="button-danger button-small" onclick="deleteUser(${user.id})">${_('Delete')}</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.editUser = function(id, username, role) {
    document.getElementById('formTitle').textContent = _('Edit');
    document.getElementById('user_id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('role').value = role;
    window.scrollTo(0, 0);
}

window.resetUserForm = function() {
    document.getElementById('formTitle').textContent = _('Add');
    document.getElementById('userForm').reset();
    document.getElementById('user_id').value = '';
}

window.handleUserFormSubmit = async function(event) {
    event.preventDefault();
    const form = event.target;
    const userId = form.user_id.value;
    const url = '/api/users';
    const method = userId ? 'PUT' : 'POST';

    const data = {
        username: form.username.value,
        password: form.password.value,
        role: form.role.value
    };
    
    if (userId) {
        data.user_id = userId;
    }

    const response = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        location.reload();
    }
}

window.deleteUser = async function(userId) {
    if (!confirm(_('Are you sure you want to delete this user?'))) return;

    const response = await fetch(`/api/users`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    });
    
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        location.reload();
    }
}

// --- Initializer ---
document.addEventListener('DOMContentLoaded', () => {
    populateForms();
    if (isAdmin) {
        fetchUsers();
    }
});