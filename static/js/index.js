import { setupMobileView, setupAnxWebDavUrl } from './page/ui.js';
import { setupEventHandlers } from './page/handlers.js';
import { t, initializeTranslations } from './page/translations.js';

document.addEventListener('DOMContentLoaded', () => {
    // --- Initialize Translations ---
    // This must be the first thing to run to ensure all UI text is translated.
    initializeTranslations();
    // --- Data ---
    const anxBooksData = JSON.parse(document.getElementById('anx-books-data').textContent);
    const calibreBooksData = JSON.parse(document.getElementById('calibre-books-data').textContent);
    const calibreErrorData = JSON.parse(document.getElementById('calibre-error-data').textContent);
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

    // --- Get Username ---
    const username = domElements.mainContainer.dataset.username;

    // Initial setup
    setupMobileView(domElements.calibreLibrary, domElements.anxLibrary, domElements.navHome, domElements.navAnx);
    setupAnxWebDavUrl(domElements.anxWebDavUrlElement, username);
    setupEventHandlers(domElements, data, currentEditing);
    window.addEventListener('resize', () => setupMobileView(domElements.calibreLibrary, domElements.anxLibrary, domElements.navHome, domElements.navAnx));
    
    // 获取并显示已推送到 Anx 的书籍标记（仅在启用活动日志时）
    const enableActivityLog = domElements.mainContainer.dataset.enableActivityLog === 'true';
    if (enableActivityLog) {
        loadPushedToAnxIndicators();
    }

    // --- Handle Calibre Error Display ---
    if (calibreErrorData) {
        const solutionElement = document.getElementById('calibre-error-solution');
        if (solutionElement) {
            let solutionText = '';
            switch (calibreErrorData.code) {
                case 'CONNECTION_ERROR':
                    solutionText = t.solutionConnectionErrorV2;
                    break;
                case 'UNAUTHORIZED':
                    solutionText = t.solutionUnauthorized;
                    break;
                case 'FORBIDDEN':
                    solutionText = t.solutionForbidden;
                    break;
                case 'HTTP_ERROR':
                    solutionText = t.solutionHttpError;
                    break;
                default:
                    solutionText = t.solutionRequestError;
                    break;
            }
            solutionElement.textContent = solutionText;
        }
    }
    
    // 获取并显示已推送到 Anx 的书籍标记
    async function loadPushedToAnxIndicators() {
        try {
            const response = await fetch('/api/user/pushed-books');
            if (!response.ok) {
                console.error('Failed to fetch pushed books:', response.statusText);
                return;
            }
            
            const pushedBookIds = await response.json();
            
            // 遍历 Calibre 书籍列表，为已推送的书籍显示标记
            pushedBookIds.forEach(bookId => {
                const bookRow = document.querySelector(`.book-row[data-book-id="${bookId}"]`);
                if (bookRow) {
                    const indicator = bookRow.querySelector('.pushed-to-anx-indicator');
                    if (indicator) {
                        indicator.style.display = 'block';
                    }
                }
            });
        } catch (error) {
            console.error('Error loading pushed to anx indicators:', error);
        }
    }
});