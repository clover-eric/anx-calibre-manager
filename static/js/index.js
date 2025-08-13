import { setupMobileView, setupAnxWebDavUrl } from './page/ui.js';
import { setupEventHandlers } from './page/handlers.js';

document.addEventListener('DOMContentLoaded', () => {
    // --- Data ---
    const anxBooksData = JSON.parse(document.getElementById('anx-books-data').textContent);
    const calibreBooksData = JSON.parse(document.getElementById('calibre-books-data').textContent);
    let currentEditing = { type: null, id: null };

    // --- DOM Elements ---
    const domElements = {
        mainContainer: document.querySelector('.main-content'),
        editModal: document.getElementById('editBookModal'),
        uploadModal: document.getElementById('uploadModal'),
        editBookForm: document.getElementById('editBookForm'),
        calibreLibrary: document.getElementById('calibre-library'),
        anxLibrary: document.getElementById('anx-library'),
        navHome: document.getElementById('nav-home'),
        navAnx: document.getElementById('nav-anx-mobile-view'),
        anxWebDavUrlElement: document.getElementById('anx-webdav-url'),
        calibreLoader: document.getElementById('calibre-loading-overlay')
    };

    const data = {
        anxBooksData,
        calibreBooksData
    };

    // Initial setup
    setupMobileView(domElements.calibreLibrary, domElements.anxLibrary, domElements.navHome, domElements.navAnx);
    setupAnxWebDavUrl(domElements.anxWebDavUrlElement, "{{ g.user.username }}");
    setupEventHandlers(domElements, data, currentEditing);
    window.addEventListener('resize', () => setupMobileView(domElements.calibreLibrary, domElements.anxLibrary, domElements.navHome, domElements.navAnx));
});