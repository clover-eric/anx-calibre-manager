const isAdmin = JSON.parse(document.getElementById('is-admin-data').textContent);

let ttsVoiceLists = {
    edge: [],
    openai: []
};

// --- Translatable Strings ---
const t = {
    smtpFromAddressTip: _('Please make sure to add the sender email address ({email}) to your Amazon Kindle trusted email list.'),
    webdavCopied: _('WebDAV address copied to clipboard'),
    copyFailed: _('Copy failed'),
    twoFAEnabled: _('2FA has been enabled.'),
    disable: _('Disable'),
    twoFANotEnabled: _('2FA is not enabled.'),
    enable: _('Enable'),
    setup2FAFailed: _('Failed to start 2FA setup.'),
    confirmDisable2FA: _('Are you sure you want to disable 2FA?'),
    noTokens: _('No available tokens.'),
    createdAt: _('Created at'),
    delete: _('Delete'),
    tokenGenerated: _('New token has been generated.'),
    generateTokenFailed: _('Failed to generate token.'),
    confirmDeleteToken: _('Are you sure you want to delete this token?'),
    confirmCleanup: _('Are you sure you want to delete ALL generated audiobook files? This action cannot be undone.'),
    cleanupFailed: _('Cleanup failed'),
    anErrorOccurred: _('An error occurred'),
    enterTestEmail: _('Please enter a test recipient email address.'),
    edit: _('Edit'),
    add: _('Add'),
    confirmDeleteUser: _('Are you sure you want to delete this user?'),
    active: _('Active'),
    disabled: _('Disabled'),
    neverExpires: _('Never expires'),
    unknown: _('Unknown'),
    generateInviteSuccess: _('Invite code generated successfully: {code}'),
    generateInviteFailed: _('Failed to generate: {error}'),
    unknownError: _('Unknown error'),
    generateInviteError: _('An error occurred while generating the invite code.'),
    operationFailedWithError: _('Operation failed: {error}'),
    operationFailed: _('Operation failed'),
    confirmDeleteInvite: _('Are you sure you want to delete this invite code?'),
    deleteFailedWithError: _('Delete failed: {error}'),
    deleteFailed: _('Delete failed'),
    // Service Config Profiles
    currentSettings: _('Current Settings'),
    enterTTSProfileName: _('Please enter a name for this TTS profile:'),
    ttsProfileSaved: _('TTS profile saved successfully!'),
    failedToSaveTTSProfile: _('Failed to save TTS profile'),
    errorSavingProfile: _('An error occurred while saving the profile'),
    selectProfileToUpdate: _('Please select a profile to update'),
    updateProfileConfirm: _('Update profile "{name}"?'),
    ttsProfileUpdated: _('TTS profile updated successfully!'),
    failedToUpdateTTSProfile: _('Failed to update TTS profile'),
    errorUpdatingProfile: _('An error occurred while updating the profile'),
    selectProfileToDelete: _('Please select a profile to delete'),
    deleteProfileConfirm: _('Delete profile "{name}"? This cannot be undone.'),
    ttsProfileDeleted: _('TTS profile deleted successfully!'),
    failedToDeleteTTSProfile: _('Failed to delete TTS profile'),
    errorDeletingProfile: _('An error occurred while deleting the profile'),
    enterLLMProfileName: _('Please enter a name for this LLM profile:'),
    llmProfileSaved: _('LLM profile saved successfully!'),
    failedToSaveLLMProfile: _('Failed to save LLM profile'),
    llmProfileUpdated: _('LLM profile updated successfully!'),
    failedToUpdateLLMProfile: _('Failed to update LLM profile'),
    llmProfileDeleted: _('LLM profile deleted successfully!'),
    failedToDeleteLLMProfile: _('Failed to delete LLM profile')
};

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
function updateTTS_UI() {
    const providerSelect = document.getElementById('tts_provider');
    const voiceInput = document.getElementById('tts_voice');
    const provider = providerSelect.value;

    // 1. Toggle visibility of provider-specific settings
    toggleTTSSettings();

    // 2. Update the voice datalist
    updateVoiceDatalist();

    // 3. Set a default voice if the current one is invalid or empty
    const currentVoice = voiceInput.value;
    const newVoiceList = ttsVoiceLists[provider] || [];

    if (!currentVoice || !newVoiceList.includes(currentVoice)) {
        if (provider === 'edge') {
            voiceInput.value = 'zh-CN-YunjianNeural';
        } else if (provider === 'openai') {
            voiceInput.value = 'alloy';
        }
    }
}

async function populateForms() {
    const userRes = await fetch('/api/user_settings');
    const userData = await userRes.json();
    document.getElementById('kindle_email').value = userData.kindle_email || '';
    document.getElementById('send_format_priority').value = (userData.send_format_priority || []).join(', ');
    document.getElementById('theme').value = userData.theme || 'auto';
    document.getElementById('force_epub_conversion').checked = userData.force_epub_conversion;
    document.getElementById('stats_enabled').checked = userData.stats_enabled;
    document.getElementById('stats_public').checked = userData.stats_public;

    // Populate TTS settings
    const ttsProviderSelect = document.getElementById('tts_provider');
    
    // Normalize provider data from backend to frontend's standard ('edge', 'openai')
    let provider = userData.tts_provider;
    if (provider === 'edge_tts') provider = 'edge';
    if (provider === 'openai_tts') provider = 'openai';
    if (!provider) provider = 'edge'; // Default value
    ttsProviderSelect.value = provider;

    document.getElementById('tts_voice').value = userData.tts_voice || '';
    document.getElementById('tts_api_key').value = userData.tts_api_key || '';
    document.getElementById('tts_base_url').value = userData.tts_base_url || '';
    document.getElementById('tts_model').value = userData.tts_model || '';
    document.getElementById('tts_rate').value = userData.tts_rate || '+0%';
    document.getElementById('tts_volume').value = userData.tts_volume || '+0%';
    document.getElementById('tts_pitch').value = userData.tts_pitch || '+0Hz';
    document.getElementById('tts_sentence_pause_ms').value = userData.tts_sentence_pause_ms || '650';
    document.getElementById('tts_paragraph_pause_ms').value = userData.tts_paragraph_pause_ms || '900';
 
     // Populate LLM settings
     document.getElementById('llm_provider').value = userData.llm_provider || 'openai';
    document.getElementById('llm_base_url').value = userData.llm_base_url || '';
    document.getElementById('llm_api_key').value = userData.llm_api_key || '';
    document.getElementById('llm_model').value = userData.llm_model || '';

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
        tipElement.textContent = t.smtpFromAddressTip.replace('{email}', userData.smtp_from_address);
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
        // 加载邀请码管理
        await loadInviteCodes();
    }
    await fetchMcpTokens();

    // Setup Koreader WebDAV URL
    const koreaderWebDavUrlElement = document.getElementById('koreader-webdav-url');
    if (koreaderWebDavUrlElement) {
        const webdavUrl = `${window.location.origin}/webdav/${userData.username}/`;
        koreaderWebDavUrlElement.textContent = webdavUrl;
        koreaderWebDavUrlElement.addEventListener('click', () => {
            navigator.clipboard.writeText(webdavUrl).then(() => {
                alert(t.webdavCopied);
            }, () => {
                alert(t.copyFailed);
            });
        });
    }

    document.getElementById('settings-loading-overlay').style.display = 'none';
    document.getElementById('userSettings').classList.add('visible');
    
    updateTTS_UI();
    toggleLLMSettings(); // Initial toggle for LLM settings
    
    // Populate LLM settings with defaults if empty
    if (isAdmin) {
        const globalRes = await fetch('/api/global_settings');
        const globalData = await globalRes.json();
        if (!document.getElementById('llm_base_url').value) {
            document.getElementById('llm_base_url').value = globalData.DEFAULT_LLM_BASE_URL || '';
        }
        if (!document.getElementById('llm_model').value) {
            document.getElementById('llm_model').value = globalData.DEFAULT_LLM_MODEL || '';
        }
    }
    
    // Fetch LLM models on initial load if credentials exist
    fetchLLMModels();
}

function toggleTTSSettings() {
    const provider = document.getElementById('tts_provider').value;
    const edgeSettings = document.querySelectorAll('.edge-setting');
    const openaiSettings = document.querySelectorAll('.openai-setting');

    // Hide all provider-specific settings first
    document.querySelectorAll('.tts-setting').forEach(el => {
        if (!el.classList.contains('edge-setting') && !el.classList.contains('openai-setting')) {
            // This is a common setting, do nothing
        } else {
            el.style.display = 'none';
        }
    });

    // Show settings for the selected provider
    if (provider === 'openai') {
        openaiSettings.forEach(el => el.style.display = 'block');
    } else { // Default to edge
        edgeSettings.forEach(el => el.style.display = 'block');
    }
}

function toggleLLMSettings() {
    const provider = document.getElementById('llm_provider').value;
    const openaiSettings = document.querySelectorAll('.openai-llm-setting');

    document.querySelectorAll('.llm-setting').forEach(el => {
        el.style.display = 'none';
    });

    if (provider === 'openai') {
        openaiSettings.forEach(el => el.style.display = 'block');
    }
}

function updateVoiceDatalist() {
    const provider = document.getElementById('tts_provider').value;
    const datalist = document.getElementById('tts_voice_list');
    
    datalist.innerHTML = '';

    const voices = ttsVoiceLists[provider] || [];

    voices.forEach(voice => {
        const option = document.createElement('option');
        option.value = voice;
        datalist.appendChild(option);
    });
}

function update2FAStatus(is_enabled) {
    const statusContainer = document.getElementById('2fa_status_container');
    if (is_enabled) {
        const enabledText = t.twoFAEnabled;
        const disableText = t.disable;
        statusContainer.innerHTML = `<p>${enabledText}</p><button type="button" class="button-danger" onclick="disable2FA()">${disableText}</button>`;
    } else {
        const notEnabledText = t.twoFANotEnabled;
        const enableText = t.enable;
        statusContainer.innerHTML = `<p>${notEnabledText}</p><button type="button" class="button" onclick="setup2FA()">${enableText}</button>`;
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
        alert(data.error || t.setup2FAFailed);
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
    if (!confirm(t.confirmDisable2FA)) return;
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
        const noTokensMessage = t.noTokens;
        listEl.innerHTML = `<p>${noTokensMessage}</p>`;
    } else {
        tokens.forEach(token => {
            const item = document.createElement('div');
            item.className = 'token-item';
            item.innerHTML = `
                <div>
                    <span class="token-value">${token.token}</span>
                    <small style="display: block; color: #666;">${t.createdAt}: ${new Date(token.created_at).toLocaleString()}</small>
                </div>
                <button class="button-danger button-small" onclick="deleteMcpToken(${token.id})">${t.delete}</button>
            `;
            listEl.appendChild(item);
        });
    }
}

window.generateMcpToken = async function() {
    const response = await fetch('/api/mcp_tokens', { method: 'POST' });
    const result = await response.json();
    if (response.ok) {
        alert(t.tokenGenerated);
        await fetchMcpTokens();
    } else {
        alert(result.error || t.generateTokenFailed);
    }
}

window.deleteMcpToken = async function(tokenId) {
    if (!confirm(t.confirmDeleteToken)) return;
    const response = await fetch(`/api/mcp_tokens/${tokenId}`, { method: 'DELETE' });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        await fetchMcpTokens();
    }
}

// --- Admin Functions ---
window.saveGlobalSettings = async function(event, force = false) {
    event.preventDefault();
    const form = event.target;
    const data = Object.fromEntries(new FormData(form).entries());

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
                <button class="button-small" onclick="editUser(${user.id}, '${user.username}', '${user.role}')">${t.edit}</button>
                <button class="button-danger button-small" onclick="deleteUser(${user.id})">${t.delete}</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.editUser = function(id, username, role) {
    document.getElementById('formTitle').textContent = t.edit;
    document.getElementById('user_id').value = id;
    document.getElementById('username').value = username;
    document.getElementById('role').value = role;
    window.scrollTo(0, 0);
}

window.resetUserForm = function() {
    document.getElementById('formTitle').textContent = t.add;
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
    if (!confirm(t.confirmDeleteUser)) return;

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
async function fetchLLMModels() {
    const baseUrl = document.getElementById('llm_base_url').value;
    const apiKey = document.getElementById('llm_api_key').value;
    const datalist = document.getElementById('llm_model_list');

    if (!baseUrl || !apiKey) {
        datalist.innerHTML = ''; // Clear list if credentials are not set
        return;
    }

    try {
        const response = await fetch('/api/llm/models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ base_url: baseUrl, api_key: apiKey })
        });

        datalist.innerHTML = ''; // Clear previous options

        if (response.ok) {
            const models = await response.json();
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                datalist.appendChild(option);
            });
        } else {
            const result = await response.json();
            console.error('Failed to fetch LLM models:', result.error);
        }
    } catch (error) {
        console.error('Error fetching LLM models:', error);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/audiobook/tts_voices');
        if (response.ok) {
            const rawVoiceLists = await response.json();
            // Adapt backend keys ('edge_tts') to frontend keys ('edge')
            ttsVoiceLists = {
                edge: rawVoiceLists.edge_tts || [],
                openai: rawVoiceLists.openai_tts || []
            };
        }
    } catch (error) {
        console.error('Failed to fetch TTS voice lists:', error);
    }

    document.getElementById('tts_provider').addEventListener('change', updateTTS_UI);
    document.getElementById('llm_provider').addEventListener('change', toggleLLMSettings);
    document.getElementById('llm_base_url').addEventListener('input', fetchLLMModels);
    document.getElementById('llm_api_key').addEventListener('input', fetchLLMModels);

    await populateForms();

    if (isAdmin) {
        await fetchUsers();
    }

    // --- Koreader Plugin Download Button ---
    const downloadBtn = document.getElementById('download-koreader-plugin-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            const url = downloadBtn.dataset.url;
            if (url) {
                window.location.href = url;
            }
        });
    }
});

// 邀请码管理函数
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
                const expiresAt = code.expires_at ? new Date(code.expires_at).toLocaleString() : t.neverExpires;
                const createdAt = new Date(code.created_at).toLocaleString();
                
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

// 邀请码加载已经在 populateForms 函数中处理

// ==================== Service Config Profiles Management ====================

// Storage for loaded profiles
let ttsProfiles = [];
let llmProfiles = [];

// --- TTS Profile Functions ---
async function loadTTSProfiles() {
    try {
        const response = await fetch('/api/service_configs/tts');
        if (response.ok) {
            ttsProfiles = await response.json();
            populateTTSProfileSelect();
        }
    } catch (error) {
        console.error('Error loading TTS profiles:', error);
    }
}

function populateTTSProfileSelect() {
    const select = document.getElementById('tts_profile_select');
    select.innerHTML = '<option value="">-- ' + t.currentSettings + ' --</option>';
    
    ttsProfiles.forEach(profile => {
        const option = document.createElement('option');
        option.value = profile.id;
        option.textContent = profile.profile_name;
        select.appendChild(option);
    });
}

function getCurrentTTSFormData() {
    return {
        provider: document.getElementById('tts_provider').value,
        voice: document.getElementById('tts_voice').value,
        api_key: document.getElementById('tts_api_key').value,
        base_url: document.getElementById('tts_base_url').value,
        model: document.getElementById('tts_model').value,
        rate: document.getElementById('tts_rate').value,
        volume: document.getElementById('tts_volume').value,
        pitch: document.getElementById('tts_pitch').value,
        sentence_pause_ms: document.getElementById('tts_sentence_pause_ms').value,
        paragraph_pause_ms: document.getElementById('tts_paragraph_pause_ms').value
    };
}

function loadTTSFormData(configData) {
    if (configData.provider) document.getElementById('tts_provider').value = configData.provider;
    if (configData.voice) document.getElementById('tts_voice').value = configData.voice;
    if (configData.api_key) document.getElementById('tts_api_key').value = configData.api_key;
    if (configData.base_url) document.getElementById('tts_base_url').value = configData.base_url;
    if (configData.model) document.getElementById('tts_model').value = configData.model;
    if (configData.rate) document.getElementById('tts_rate').value = configData.rate;
    if (configData.volume) document.getElementById('tts_volume').value = configData.volume;
    if (configData.pitch) document.getElementById('tts_pitch').value = configData.pitch;
    if (configData.sentence_pause_ms) document.getElementById('tts_sentence_pause_ms').value = configData.sentence_pause_ms;
    if (configData.paragraph_pause_ms) document.getElementById('tts_paragraph_pause_ms').value = configData.paragraph_pause_ms;
    
    updateTTS_UI();
}

window.onTTSProfileChange = function() {
    const select = document.getElementById('tts_profile_select');
    const profileId = select.value;
    
    if (!profileId) return;
    
    const profile = ttsProfiles.find(p => p.id == profileId);
    if (profile) {
        loadTTSFormData(profile.config_data);
    }
};

window.saveTTSProfileAsNew = async function() {
    const profileName = prompt(t.enterTTSProfileName);
    if (!profileName || !profileName.trim()) return;
    
    const configData = getCurrentTTSFormData();
    
    try {
        const response = await fetch('/api/service_configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config_type: 'tts',
                profile_name: profileName.trim(),
                config_data: configData
            })
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(t.ttsProfileSaved);
            await loadTTSProfiles();
        } else {
            alert(result.error || t.failedToSaveTTSProfile);
        }
    } catch (error) {
        alert(t.errorSavingProfile);
        console.error(error);
    }
};

window.updateTTSProfile = async function() {
    const select = document.getElementById('tts_profile_select');
    const profileId = select.value;
    
    if (!profileId) {
        alert(t.selectProfileToUpdate);
        return;
    }
    
    const profile = ttsProfiles.find(p => p.id == profileId);
    if (!profile) return;
    
    if (!confirm(t.updateProfileConfirm.replace('{name}', profile.profile_name))) return;
    
    const configData = getCurrentTTSFormData();
    
    try {
        const response = await fetch(`/api/service_configs/${profileId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_name: profile.profile_name,
                config_data: configData
            })
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(t.ttsProfileUpdated);
            await loadTTSProfiles();
        } else {
            alert(result.error || t.failedToUpdateTTSProfile);
        }
    } catch (error) {
        alert(t.errorUpdatingProfile);
        console.error(error);
    }
};

window.deleteTTSProfile = async function() {
    const select = document.getElementById('tts_profile_select');
    const profileId = select.value;
    
    if (!profileId) {
        alert(t.selectProfileToDelete);
        return;
    }
    
    const profile = ttsProfiles.find(p => p.id == profileId);
    if (!profile) return;
    
    if (!confirm(t.deleteProfileConfirm.replace('{name}', profile.profile_name))) return;
    
    try {
        const response = await fetch(`/api/service_configs/${profileId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(t.ttsProfileDeleted);
            await loadTTSProfiles();
            select.value = '';
        } else {
            alert(result.error || t.failedToDeleteTTSProfile);
        }
    } catch (error) {
        alert(t.errorDeletingProfile);
        console.error(error);
    }
};

// --- LLM Profile Functions ---
async function loadLLMProfiles() {
    try {
        const response = await fetch('/api/service_configs/llm');
        if (response.ok) {
            llmProfiles = await response.json();
            populateLLMProfileSelect();
        }
    } catch (error) {
        console.error('Error loading LLM profiles:', error);
    }
}

function populateLLMProfileSelect() {
    const select = document.getElementById('llm_profile_select');
    select.innerHTML = '<option value="">-- ' + t.currentSettings + ' --</option>';
    
    llmProfiles.forEach(profile => {
        const option = document.createElement('option');
        option.value = profile.id;
        option.textContent = profile.profile_name;
        select.appendChild(option);
    });
}

function getCurrentLLMFormData() {
    return {
        provider: document.getElementById('llm_provider').value,
        base_url: document.getElementById('llm_base_url').value,
        api_key: document.getElementById('llm_api_key').value,
        model: document.getElementById('llm_model').value
    };
}

function loadLLMFormData(configData) {
    if (configData.provider) document.getElementById('llm_provider').value = configData.provider;
    if (configData.base_url) document.getElementById('llm_base_url').value = configData.base_url;
    if (configData.api_key) document.getElementById('llm_api_key').value = configData.api_key;
    if (configData.model) document.getElementById('llm_model').value = configData.model;
    
    toggleLLMSettings();
    fetchLLMModels();
}

window.onLLMProfileChange = function() {
    const select = document.getElementById('llm_profile_select');
    const profileId = select.value;
    
    if (!profileId) return;
    
    const profile = llmProfiles.find(p => p.id == profileId);
    if (profile) {
        loadLLMFormData(profile.config_data);
    }
};

window.saveLLMProfileAsNew = async function() {
    const profileName = prompt(_('Please enter a name for this LLM profile:'));
    if (!profileName || !profileName.trim()) return;
    
    const configData = getCurrentLLMFormData();
    
    try {
        const response = await fetch('/api/service_configs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                config_type: 'llm',
                profile_name: profileName.trim(),
                config_data: configData
            })
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(_('LLM profile saved successfully!'));
            await loadLLMProfiles();
        } else {
            alert(result.error || _('Failed to save LLM profile'));
        }
    } catch (error) {
        alert(_('An error occurred while saving the profile'));
        console.error(error);
    }
};

window.updateLLMProfile = async function() {
    const select = document.getElementById('llm_profile_select');
    const profileId = select.value;
    
    if (!profileId) {
        alert(_('Please select a profile to update'));
        return;
    }
    
    const profile = llmProfiles.find(p => p.id == profileId);
    if (!profile) return;
    
    if (!confirm(_('Update profile "{name}"?').replace('{name}', profile.profile_name))) return;
    
    const configData = getCurrentLLMFormData();
    
    try {
        const response = await fetch(`/api/service_configs/${profileId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                profile_name: profile.profile_name,
                config_data: configData
            })
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(_('LLM profile updated successfully!'));
            await loadLLMProfiles();
        } else {
            alert(result.error || _('Failed to update LLM profile'));
        }
    } catch (error) {
        alert(_('An error occurred while updating the profile'));
        console.error(error);
    }
};

window.deleteLLMProfile = async function() {
    const select = document.getElementById('llm_profile_select');
    const profileId = select.value;
    
    if (!profileId) {
        alert(_('Please select a profile to delete'));
        return;
    }
    
    const profile = llmProfiles.find(p => p.id == profileId);
    if (!profile) return;
    
    if (!confirm(_('Delete profile "{name}"? This cannot be undone.').replace('{name}', profile.profile_name))) return;
    
    try {
        const response = await fetch(`/api/service_configs/${profileId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        if (response.ok) {
            alert(_('LLM profile deleted successfully!'));
            await loadLLMProfiles();
            select.value = '';
        } else {
            alert(result.error || _('Failed to delete LLM profile'));
        }
    } catch (error) {
        alert(_('An error occurred while deleting the profile'));
        console.error(error);
    }
};

// Initialize profile management after DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    // Load profiles
    await loadTTSProfiles();
    await loadLLMProfiles();
    
    // Attach event listeners
    const ttsProfileSelect = document.getElementById('tts_profile_select');
    const llmProfileSelect = document.getElementById('llm_profile_select');
    
    if (ttsProfileSelect) {
        ttsProfileSelect.addEventListener('change', onTTSProfileChange);
    }
    
    if (llmProfileSelect) {
        llmProfileSelect.addEventListener('change', onLLMProfileChange);
    }
    
    // Attach button event listeners
    const saveTTSBtn = document.getElementById('save_tts_profile_as_new');
    const updateTTSBtn = document.getElementById('update_tts_profile');
    const deleteTTSBtn = document.getElementById('delete_tts_profile');
    
    if (saveTTSBtn) saveTTSBtn.addEventListener('click', saveTTSProfileAsNew);
    if (updateTTSBtn) updateTTSBtn.addEventListener('click', updateTTSProfile);
    if (deleteTTSBtn) deleteTTSBtn.addEventListener('click', deleteTTSProfile);
    
    const saveLLMBtn = document.getElementById('save_llm_profile_as_new');
    const updateLLMBtn = document.getElementById('update_llm_profile');
    const deleteLLMBtn = document.getElementById('delete_llm_profile');
    
    if (saveLLMBtn) saveLLMBtn.addEventListener('click', saveLLMProfileAsNew);
    if (updateLLMBtn) updateLLMBtn.addEventListener('click', updateLLMProfile);
    if (deleteLLMBtn) deleteLLMBtn.addEventListener('click', deleteLLMProfile);
});