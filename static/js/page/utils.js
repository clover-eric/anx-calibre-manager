// --- API Helper ---
export function fetch_with_token(url, options) {
    // Ensure that session cookies are sent with every API request.
    // This is crucial for backend services like i18n that rely on session data.
    const newOptions = { ...options, credentials: 'same-origin' };
    return fetch(url, newOptions);
}

// --- Modal Controls ---
export const showModal = (modal) => modal.style.display = 'block';
export const hideModal = (modal) => modal.style.display = 'none';

// --- Navigation with Loader ---
export function showLoaderAndNavigate(url, calibreLoader) {
    if (calibreLoader) {
        calibreLoader.style.display = 'flex';
    }
    setTimeout(() => {
        window.location.href = url;
    }, 50);
}