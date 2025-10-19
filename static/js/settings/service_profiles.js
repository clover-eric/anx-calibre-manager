// ==================== Service Config Profiles Management ====================
// This file handles TTS and LLM configuration profile management

// Storage for loaded profiles
let ttsProfiles = [];
let llmProfiles = [];

// --- TTS Profile Functions ---

/**
 * Load all TTS profiles from the server
 */
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

/**
 * Populate the TTS profile select dropdown
 */
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

/**
 * Get current TTS form data
 * @returns {Object} TTS configuration data
 */
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

/**
 * Load TTS form data from a profile
 * @param {Object} configData - TTS configuration data
 */
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

/**
 * Handle TTS profile selection change
 */
window.onTTSProfileChange = function() {
    const select = document.getElementById('tts_profile_select');
    const profileId = select.value;
    
    if (!profileId) return;
    
    const profile = ttsProfiles.find(p => p.id == profileId);
    if (profile) {
        loadTTSFormData(profile.config_data);
    }
};

/**
 * Save current TTS settings as a new profile
 */
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

/**
 * Update the currently selected TTS profile
 */
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

/**
 * Delete the currently selected TTS profile
 */
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

/**
 * Load all LLM profiles from the server
 */
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

/**
 * Populate the LLM profile select dropdown
 */
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

/**
 * Get current LLM form data
 * @returns {Object} LLM configuration data
 */
function getCurrentLLMFormData() {
    return {
        provider: document.getElementById('llm_provider').value,
        base_url: document.getElementById('llm_base_url').value,
        api_key: document.getElementById('llm_api_key').value,
        model: document.getElementById('llm_model').value
    };
}

/**
 * Load LLM form data from a profile
 * @param {Object} configData - LLM configuration data
 */
function loadLLMFormData(configData) {
    if (configData.provider) document.getElementById('llm_provider').value = configData.provider;
    if (configData.base_url) document.getElementById('llm_base_url').value = configData.base_url;
    if (configData.api_key) document.getElementById('llm_api_key').value = configData.api_key;
    if (configData.model) document.getElementById('llm_model').value = configData.model;
    
    toggleLLMSettings();
    fetchLLMModels();
}

/**
 * Handle LLM profile selection change
 */
window.onLLMProfileChange = function() {
    const select = document.getElementById('llm_profile_select');
    const profileId = select.value;
    
    if (!profileId) return;
    
    const profile = llmProfiles.find(p => p.id == profileId);
    if (profile) {
        loadLLMFormData(profile.config_data);
    }
};

/**
 * Save current LLM settings as a new profile
 */
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

/**
 * Update the currently selected LLM profile
 */
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

/**
 * Delete the currently selected LLM profile
 */
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