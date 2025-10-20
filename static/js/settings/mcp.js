// ==================== MCP Token Logic ====================
// This file handles MCP token management functionality

/**
 * Fetch and display all MCP tokens for the current user
 */
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
                    <small style="display: block; color: #666;">${t.createdAt}: ${formatLocalTime(token.created_at)}</small>
                </div>
                <button class="button-danger button-small" onclick="deleteMcpToken(${token.id})">${t.delete}</button>
            `;
            listEl.appendChild(item);
        });
    }
}

/**
 * Generate a new MCP token
 */
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

/**
 * Delete an MCP token
 * @param {number} tokenId - The ID of the token to delete
 */
window.deleteMcpToken = async function(tokenId) {
    if (!confirm(t.confirmDeleteToken)) return;
    const response = await fetch(`/api/mcp_tokens/${tokenId}`, { method: 'DELETE' });
    const result = await response.json();
    alert(result.message || result.error);
    if (response.ok) {
        await fetchMcpTokens();
    }
}