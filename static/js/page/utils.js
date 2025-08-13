// --- API Helper ---
export function fetch_with_token(url, options) {
    return fetch(url, { ...options });
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