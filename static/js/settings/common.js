// ==================== Common Variables and Translations ====================
// This file contains shared variables and translatable strings used across all settings modules

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