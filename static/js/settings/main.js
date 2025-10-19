// ==================== Main Initializer ====================
// This file initializes and coordinates all settings modules

/**
 * Initialize all settings page functionality
 */
document.addEventListener('DOMContentLoaded', async () => {
    // Fetch TTS voice lists
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

    // Attach event listeners for TTS and LLM providers
    document.getElementById('tts_provider').addEventListener('change', updateTTS_UI);
    document.getElementById('llm_provider').addEventListener('change', toggleLLMSettings);
    document.getElementById('llm_base_url').addEventListener('input', fetchLLMModels);
    document.getElementById('llm_api_key').addEventListener('input', fetchLLMModels);

    // Populate all forms with data from server
    await populateForms();

    // Load user management for admin
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
    
    // Load TTS and LLM profiles
    await loadTTSProfiles();
    await loadLLMProfiles();
    
    // Attach event listeners for profile selection
    const ttsProfileSelect = document.getElementById('tts_profile_select');
    const llmProfileSelect = document.getElementById('llm_profile_select');
    
    if (ttsProfileSelect) {
        ttsProfileSelect.addEventListener('change', onTTSProfileChange);
    }
    
    if (llmProfileSelect) {
        llmProfileSelect.addEventListener('change', onLLMProfileChange);
    }
    
    // Attach button event listeners for TTS profiles
    const saveTTSBtn = document.getElementById('save_tts_profile_as_new');
    const updateTTSBtn = document.getElementById('update_tts_profile');
    const deleteTTSBtn = document.getElementById('delete_tts_profile');
    
    if (saveTTSBtn) saveTTSBtn.addEventListener('click', saveTTSProfileAsNew);
    if (updateTTSBtn) updateTTSBtn.addEventListener('click', updateTTSProfile);
    if (deleteTTSBtn) deleteTTSBtn.addEventListener('click', deleteTTSProfile);
    
    // Attach button event listeners for LLM profiles
    const saveLLMBtn = document.getElementById('save_llm_profile_as_new');
    const updateLLMBtn = document.getElementById('update_llm_profile');
    const deleteLLMBtn = document.getElementById('delete_llm_profile');
    
    if (saveLLMBtn) saveLLMBtn.addEventListener('click', saveLLMProfileAsNew);
    if (updateLLMBtn) updateLLMBtn.addEventListener('click', updateLLMProfile);
    if (deleteLLMBtn) deleteLLMBtn.addEventListener('click', deleteLLMProfile);
});