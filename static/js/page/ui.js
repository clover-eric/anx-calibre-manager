import { showModal } from './utils.js';
import { setupCompletions } from './completions.js';

// --- Edit Modal Population ---
export function populateAnxEditForm(book, currentEditing, editBookForm, editModal) {
    currentEditing.type = 'anx';
    currentEditing.id = book.id;
    
    // 提取翻译字符串，让Babel能够识别
    const titleLabel = _('Title');
    const authorLabel = _('Author');
    const ratingLabel = _('Rating (0-5)');
    const progressLabel = _('Reading Progress (%)');
    const descriptionLabel = _('Description');
    
    editBookForm.innerHTML = `
        <div class="form-group"><label>${titleLabel}:</label><input type="text" name="title" value="${book.title || ''}"></div>
        <div class="form-group"><label>${authorLabel}:</label><input type="text" name="author" value="${book.author || ''}"></div>
        <div class="form-group"><label>${ratingLabel}:</label><input type="number" name="rating" min="0" max="5" step="0.5" value="${book.rating || 0}"></div>
        <div class="form-group"><label>${progressLabel}:</label><input type="number" name="reading_percentage" min="0" max="100" step="0.1" value="${(book.reading_percentage * 100).toFixed(1)}"></div>
        <div class="form-group">
            <label>${descriptionLabel}:</label>
            <div class="textarea-container">
                <button type="button" class="toggle-fullscreen-btn" data-action="toggle-fullscreen"><i class="fas fa-expand"></i></button>
                <textarea name="description">${book.description || ''}</textarea>
            </div>
        </div>
    `;
    showModal(editModal);
}

export function populateCalibreEditForm(book, currentEditing, editBookForm, editModal) {
    currentEditing.type = 'calibre';
    currentEditing.id = book.id;
    // Helper to get nested custom field values safely
    const getCustom = (field) => (book.user_metadata[field] ? book.user_metadata[field]['#value#'] : null) || '';
    
    const pubdateRaw = book.pubdate;
    const pubdate = (pubdateRaw && !pubdateRaw.startsWith('0101-01')) ? pubdateRaw.split('T')[0] : '';

    const readdateRaw = getCustom('#readdate');
    const readdate = (readdateRaw && !readdateRaw.startsWith('0101-01')) ? readdateRaw.split('T')[0] : '';

    // 提取翻译字符串，让Babel能够识别
    const noteLabel = _('Note');
    const metadataNote = _('Metadata updates for Calibre books are asynchronous and may take a moment to apply.');
    const titleLabel = _('Title');
    const authorsLabel = _('Authors (comma-separated)');
    const publisherLabel = _('Publisher');
    const pubDateLabel = _('Publication Date');
    const ratingLabel = _('Rating (0-5)');
    const tagsLabel = _('Tags (comma-separated)');
    const libraryLabel = _('Library (custom field #library)');
    const readDateLabel = _('Read Date (custom field #readdate)');
    const descriptionLabel = _('Description');

    editBookForm.innerHTML = `
        <p><strong>${noteLabel}:</strong> ${metadataNote}</p>
        <div class="form-group"><label>${titleLabel}:</label><input type="text" name="title" value="${book.title || ''}"></div>
        <div class="form-group autocomplete-container"><label>${authorsLabel}:</label><input type="text" name="authors" value="${book.authors.join(', ')}" autocomplete="off" data-completion-field="authors"></div>
        <div class="form-group autocomplete-container"><label>${publisherLabel}:</label><input type="text" name="publisher" value="${book.publisher || ''}" autocomplete="off" data-completion-field="publisher"></div>
        <div class="form-group"><label>${pubDateLabel}:</label><input type="date" name="pubdate" value="${pubdate}"></div>
        <div class="form-group"><label>${ratingLabel}:</label><input type="number" name="rating" min="0" max="5" step="0.5" value="${book.rating || 0}"></div>
        <div class="form-group autocomplete-container"><label>${tagsLabel}:</label><input type="text" name="tags" value="${book.tags.join(', ')}" autocomplete="off" data-completion-field="tags"></div>
        <div class="form-group autocomplete-container"><label>${libraryLabel}:</label><input type="text" name="#library" value="${getCustom('#library')}" autocomplete="off" data-completion-field="#library"></div>
        <div class="form-group"><label>${readDateLabel}:</label><input type="date" name="#readdate" value="${readdate}"></div>
        <div class="form-group">
            <label>${descriptionLabel}:</label>
            <div class="textarea-container">
                <button type="button" class="toggle-fullscreen-btn" data-action="toggle-fullscreen"><i class="fas fa-expand"></i></button>
                <textarea name="comments" rows="4">${book.comments || ''}</textarea>
            </div>
        </div>
    `;
    showModal(editModal);
    setupCompletions(editBookForm);
}

// --- Button Animation Handler ---
export function handleButtonAnimation(button, apiPromise) {
    if (button.classList.contains('in-progress')) return;

    const buttonText = button.querySelector('.button-text');
    const originalText = buttonText.textContent;

    let progressOverlay = button.querySelector('.progress-overlay');
    if (!progressOverlay) {
        progressOverlay = document.createElement('div');
        progressOverlay.className = 'progress-overlay';
        button.appendChild(progressOverlay);
    }
    
    button.classList.add('in-progress');
    buttonText.textContent = _('Processing...');
    
    setTimeout(() => {
        progressOverlay.style.width = '95%';
    }, 10);

    apiPromise
        .then(data => {
            progressOverlay.style.width = '100%';
            button.classList.add('is-success');
            buttonText.textContent = _('Success!');

            setTimeout(() => {
                button.classList.remove('in-progress', 'is-success');
                buttonText.textContent = originalText;
                progressOverlay.style.transition = 'width 0s';
                progressOverlay.style.width = '0%';
                setTimeout(() => {
                    progressOverlay.style.transition = 'width 1.5s ease-out';
                }, 50);

                if (originalText === "Anx") {
                    location.reload();
                }
            }, 7000);
        })
        .catch(error => {
            alert(`${_('Error')}: ${error.message}`);
            button.classList.remove('in-progress');
            buttonText.textContent = originalText;
            progressOverlay.style.transition = 'width 0s';
            progressOverlay.style.width = '0%';
             setTimeout(() => {
                progressOverlay.style.transition = 'width 1.5s ease-out';
            }, 50);
        });
}

// --- Mobile View Logic ---
export function setupMobileView(calibreLibrary, anxLibrary, navHome, navAnx) {
    if (window.innerWidth > 768) {
        calibreLibrary.style.display = 'flex';
        anxLibrary.style.display = 'flex';
        return;
    }

    const activeView = localStorage.getItem('mobileView') || 'calibre';
    if (activeView === 'anx') {
        calibreLibrary.style.display = 'none';
        anxLibrary.style.display = 'flex';
        navAnx.classList.add('active');
        navHome.classList.remove('active');
    } else {
        calibreLibrary.style.display = 'flex';
        anxLibrary.style.display = 'none';
        navHome.classList.add('active');
        navAnx.classList.remove('active');
    }
}

// --- Anx WebDAV URL ---
export function setupAnxWebDavUrl(anxWebDavUrlElement, username) {
    if (anxWebDavUrlElement) {
        const protocol = window.location.protocol;
        const host = window.location.host;
        const url = `${protocol}//${host}/webdav/${username}`;
        anxWebDavUrlElement.textContent = url;
    }
}