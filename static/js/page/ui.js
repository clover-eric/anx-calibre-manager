import { showModal } from './utils.js';
import { setupCompletions } from './completions.js';
import { t } from './translations.js';

function getTranslatedMessage(task) {
    if (!task || !task.status_key) {
        return t.processing; // Default message
    }

    let message = t[task.status_key] || task.status_key; // Fallback to key if not found

    if (task.status_params) {
        try {
            // The params from backend are a JSON string
            const params = typeof task.status_params === 'string' ? JSON.parse(task.status_params) : task.status_params;
            for (const key in params) {
                // Use a regex to handle both %(key)s and %(key)d formats, etc.
                const regex = new RegExp(`%\\(${key}\\)[sd]`, "g");
                message = message.replace(regex, params[key]);
            }
        } catch (e) {
            console.error("Failed to parse or apply status_params", e);
        }
    }
    return message;
}

// --- Edit Modal Population ---
export function populateAnxEditForm(book, currentEditing, editBookForm, editModal) {
    currentEditing.type = 'anx';
    currentEditing.id = book.id;
    
    editBookForm.innerHTML = `
        <div class="form-group"><label>${t.title}:</label><input type="text" name="title" value="${book.title || ''}"></div>
        <div class="form-group"><label>${t.author}:</label><input type="text" name="author" value="${book.author || ''}"></div>
        <div class="form-group"><label>${t.rating}:</label><input type="number" name="rating" min="0" max="5" step="0.5" value="${book.rating || 0}"></div>
        <div class="form-group"><label>${t.readingProgress}:</label><input type="number" name="reading_percentage" min="0" max="100" step="0.1" value="${(book.reading_percentage * 100).toFixed(1)}"></div>
        <div class="form-group">
            <label>${t.description}:</label>
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

    editBookForm.innerHTML = `
        <p><strong>${t.note}:</strong> ${t.metadataNote}</p>
        <div class="form-group"><label>${t.title}:</label><input type="text" name="title" value="${book.title || ''}"></div>
        <div class="form-group autocomplete-container"><label>${t.authors}:</label><input type="text" name="authors" value="${book.authors.join(', ')}" autocomplete="off" data-completion-field="authors"></div>
        <div class="form-group autocomplete-container"><label>${t.publisher}:</label><input type="text" name="publisher" value="${book.publisher || ''}" autocomplete="off" data-completion-field="publisher"></div>
        <div class="form-group"><label>${t.pubDate}:</label><input type="date" name="pubdate" value="${pubdate}"></div>
        <div class="form-group"><label>${t.rating}:</label><input type="number" name="rating" min="0" max="5" step="0.5" value="${book.rating || 0}"></div>
        <div class="form-group autocomplete-container"><label>${t.tags}:</label><input type="text" name="tags" value="${book.tags.join(', ')}" autocomplete="off" data-completion-field="tags"></div>
        <div class="form-group autocomplete-container"><label>${t.library}:</label><input type="text" name="#library" value="${getCustom('#library')}" autocomplete="off" data-completion-field="#library"></div>
        <div class="form-group"><label>${t.readDate}:</label><input type="date" name="#readdate" value="${readdate}"></div>
        <div class="form-group">
            <label>${t.description}:</label>
            <div class="textarea-container">
                <button type="button" class="toggle-fullscreen-btn" data-action="toggle-fullscreen"><i class="fas fa-expand"></i></button>
                <textarea name="comments" rows="4">${book.comments || ''}</textarea>
            </div>
        </div>
    `;
    showModal(editModal);
    setupCompletions(editBookForm);
}

// --- Audiobook Button UI Handlers ---
export function updateAudiobookButtonProgress(button, task) {
    const buttonText = button.querySelector('.button-text');
    let progressOverlay = button.querySelector('.progress-overlay');

    if (!button.classList.contains('in-progress')) {
        button.classList.add('in-progress');
        if (!progressOverlay) {
            progressOverlay = document.createElement('div');
            progressOverlay.className = 'progress-overlay';
            button.appendChild(progressOverlay);
        }
    }
    
    const percentage = task.percentage || 0;
    const message = getTranslatedMessage(task);
    
    buttonText.textContent = message;
    progressOverlay.style.width = `${percentage}%`;
}

export function finalizeAudiobookButton(button, task, originalText) {
    const library = button.dataset.library; // Get library from original button
    const buttonText = button.querySelector('.button-text');
    const progressOverlay = button.querySelector('.progress-overlay');
    const status = task.status;

    if (status === 'success') {
        button.classList.remove('in-progress');
        button.classList.add('is-success');
        buttonText.textContent = t.downloadAudiobook;

        // Create a container for the new buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'audiobook-actions-container';

        // Create Listen button
        const listenButton = document.createElement('button');
        listenButton.dataset.action = 'listen-audiobook';
        listenButton.dataset.taskId = task.task_id;
        listenButton.dataset.library = library; // Add library to the new button
        listenButton.textContent = t.listenAudiobook;
        listenButton.className = 'button listen-button';
        buttonContainer.appendChild(listenButton);

        // Create Download button
        const downloadLink = document.createElement('a');
        downloadLink.href = `/api/audiobook/download/${task.task_id}`;
        downloadLink.textContent = t.downloadAudiobook;
        downloadLink.className = 'button is-success';
        buttonContainer.appendChild(downloadLink);
        
        button.parentNode.replaceChild(buttonContainer, button);

    } else { // error
        button.classList.remove('in-progress');
        button.classList.add('is-failure');
        buttonText.textContent = t.failed;
        const message = getTranslatedMessage(task);
        alert(`${t.error}: ${message}`);

        setTimeout(() => {
            button.classList.remove('is-failure');
            buttonText.textContent = originalText;
            if (progressOverlay) {
                progressOverlay.style.width = '0%';
            }
        }, 5000);
    }
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
    buttonText.textContent = t.processing;
    
    setTimeout(() => {
        progressOverlay.style.width = '95%';
    }, 10);

    apiPromise
        .then(data => {
            progressOverlay.style.width = '100%';
            button.classList.add('is-success');
            buttonText.textContent = t.success;

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
            alert(`${t.error}: ${error.message}`);
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