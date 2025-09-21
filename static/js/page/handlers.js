import { fetch_with_token, showModal, hideModal, showLoaderAndNavigate } from './utils.js';
import {
    populateAnxEditForm,
    populateCalibreEditForm,
    handleButtonAnimation,
    updateAudiobookButtonProgress,
    finalizeAudiobookButton
} from './ui.js';
import { t } from './translations.js';


function pollAudiobookStatus(taskId, button, originalText) {
    const intervalId = setInterval(() => {
        fetch_with_token(`/api/audiobook/status/${taskId}`)
            .then(res => {
                if (!res.ok) throw new Error(t.networkResponseNotOk);
                return res.json();
            })
            .then(data => {
                if (data.status === 'progress' || data.status === 'queued' || data.status === 'start' || data.status === 'processing') {
                    // Pass the whole task object to the UI function
                    updateAudiobookButtonProgress(button, data);
                } else {
                    clearInterval(intervalId);
                    // Pass the whole task object to finalize
                    finalizeAudiobookButton(button, data, originalText);
                }
            })
            .catch(error => {
                clearInterval(intervalId);
                let errorKey = 'UNKNOWN_ERROR';
                let errorParams = { error: error.message };

                // Check for a network error specifically
                if (error instanceof TypeError && error.message.toLowerCase().includes('failed to fetch')) {
                    errorKey = 'NETWORK_ERROR';
                    errorParams = {}; // No params needed for this specific key
                }
                
                // Create a task-like object for error display
                const errorData = { status: 'error', status_key: errorKey, status_params: errorParams };
                finalizeAudiobookButton(button, errorData, originalText);
            });
    }, 2000);
}

function initializeAudiobookButtons() {
    const audiobookButtons = document.querySelectorAll('[data-action="generate-audiobook"]');
    audiobookButtons.forEach(button => {
        const bookId = button.dataset.id;
        const library = button.dataset.library;
        const buttonText = button.querySelector('.button-text');
        const originalText = buttonText.textContent;

        fetch_with_token(`/api/audiobook/status_for_book?book_id=${bookId}&library=${library}`)
            .then(res => res.json())
            .then(task => {
                // If a task object is returned and has a status
                if (task && task.status) {
                    if (task.status === 'success') {
                        finalizeAudiobookButton(button, task, originalText);
                    } else if (task.status === 'error') {
                        // Don't show permanent error on load, just reset the button
                        console.log(`Task for book ${bookId} found with error state. Button reset.`);
                    } else {
                        // Task is in progress
                        updateAudiobookButtonProgress(button, task);
                        pollAudiobookStatus(task.task_id, button, originalText);
                    }
                }
            })
            .catch(error => {
                // Don't alert the user on load, just log it. It might be a network blip.
                console.error(`[Audiobook Status] Failed to fetch status for book ${bookId}. Error:`, error);
            });
    });
}


function handleSaveChanges(saveButton, editBookForm, currentEditing, anxBooksData, calibreBooksData, editModal) {
    const formData = new FormData(editBookForm);
    const currentData = Object.fromEntries(formData.entries());

    // If the rating is an empty string, treat it as a null value (e.g., 0) to avoid backend type errors.
    if (currentData.rating === '') {
        currentData.rating = '0';
    }

    let url;
    let payload = {};

    if (currentEditing.type === 'anx') {
        url = `/api/edit_anx_metadata`;
        const originalBook = anxBooksData.find(b => b.id == currentEditing.id);
        payload = { id: currentEditing.id };
        
        for (const key in currentData) {
            if (key === 'id') continue;
            let originalValue = originalBook[key];
            let currentValue = currentData[key];

            if (key === 'reading_percentage') {
                currentValue = parseFloat(currentValue) / 100.0;
            }
            if (key === 'rating') {
                originalValue = originalValue || 0;
            }

            if (String(originalValue || '') !== String(currentValue)) {
                payload[key] = currentValue;
            }
        }

    } else { // calibre
        url = `/api/update_calibre_book/${currentEditing.id}`;
        const originalBook = calibreBooksData.find(b => b.id == currentEditing.id);
        
        const getOrigCustom = (field) => (originalBook.user_metadata[field] ? originalBook.user_metadata[field]['#value#'] : null) || '';

        for (const key in currentData) {
            let originalValue;
            let currentValue = currentData[key];

            switch(key) {
                case 'authors':
                    originalValue = originalBook.authors.join(', ');
                    break;
                case 'tags':
                    originalValue = originalBook.tags.join(', ');
                    break;
                case 'pubdate':
                    const pubdateRaw = originalBook.pubdate;
                    originalValue = (pubdateRaw && !pubdateRaw.startsWith('0101-01-01')) ? pubdateRaw.split('T')[0] : '';
                    break;
                case '#readdate':
                    const readdateRaw = getOrigCustom('#readdate');
                    originalValue = (readdateRaw && !readdateRaw.startsWith('0101-01-01')) ? readdateRaw.split('T')[0] : '';
                    break;
                case '#library':
                    originalValue = getOrigCustom('#library');
                    break;
                case 'rating':
                    originalValue = originalBook[key] || 0;
                    if (String(originalValue) !== String(currentValue)) {
                         // Convert rating from 0-5 scale to 0-10 for Calibre's set_fields API
                         payload[key] = parseFloat(currentValue) * 2;
                    }
                    continue; // Skip the generic comparison below
                default:
                    originalValue = originalBook[key] || '';
            }
            
            if (String(originalValue) !== String(currentValue)) {
                payload[key] = currentValue;
            }
        }
    }
    
    const changeKeys = Object.keys(payload);
    if (changeKeys.length === 0 || (changeKeys.length === 1 && changeKeys[0] === 'id')) {
         alert(t.noChangesDetected);
         return;
    }

    const apiCall = fetch_with_token(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(res => {
        if (!res.ok) return res.json().then(err => { throw new Error(err.error) });
        return res.json();
    }).then(result => {
        setTimeout(() => {
            hideModal(editModal);
            location.reload();
        }, 1000);
        return result;
    });

    handleButtonAnimation(saveButton, apiCall);
}

export function setupEventHandlers(
    {
        uploadModal,
        editModal,
        editBookForm,
        calibreLoader
    },
    {
        anxBooksData,
        calibreBooksData
    },
    currentEditing
) {
    document.body.addEventListener('click', (e) => {
        const target = e.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const id = target.dataset.id;
        
        switch (action) {
            case 'generate-audiobook': {
                if (target.classList.contains('in-progress')) break;

                const library = target.dataset.library;
                const bookId = target.dataset.id;
                const buttonText = target.querySelector('.button-text');
                const originalText = buttonText.textContent;

                const formData = new FormData();
                formData.append('book_id', bookId);
                formData.append('library', library);

                // Update button immediately with a status object
                updateAudiobookButtonProgress(target, { status: 'queued', status_key: 'QUEUED', percentage: 0 });

                fetch_with_token('/api/audiobook/generate', {
                    method: 'POST',
                    body: formData
                })
                .then(async res => {
                    const data = await res.json();
                    if (!res.ok) {
                        const error = new Error(data.error);
                        // If task already exists, server returns 409 with the task_id
                        if (res.status === 409 && data.task_id) {
                            error.task_id = data.task_id;
                        }
                        throw error;
                    }
                    return data;
                })
                .then(data => {
                    pollAudiobookStatus(data.task_id, target, originalText);
                })
                .catch(error => {
                    if (error.task_id) {
                        // This is a conflict (409), task already exists, so just start polling
                        pollAudiobookStatus(error.task_id, target, originalText);
                    } else {
                        // This is a different error, create a task-like object for display
                        const errorData = { status: 'error', status_key: 'UNKNOWN_ERROR', status_params: { error: error.message } };
                        finalizeAudiobookButton(target, errorData, originalText);
                    }
                });
                break;
            }
            case 'show-upload-modal':
                showModal(uploadModal);
                break;
            case 'close-modal':
                hideModal(target.closest('.modal'));
                break;
            case 'edit-anx': {
                const book = anxBooksData.find(b => b.id == id);
                if (book) populateAnxEditForm(book, currentEditing, editBookForm, editModal);
                break;
            }
            case 'edit-calibre': {
                const book = calibreBooksData.find(b => b.id == id);
                if (book) populateCalibreEditForm(book, currentEditing, editBookForm, editModal);
                break;
            }
            case 'delete-anx':
                if (confirm(t.confirmDeleteBook)) {
                    fetch_with_token(`/api/delete_anx_book/${id}`, { method: 'DELETE' })
                        .then(res => res.json()).then(data => {
                            alert(data.message || data.error);
                            if (data.message) location.reload();
                        });
                }
                break;
            case 'push-to-anx': {
                const apiCall = fetch_with_token(`/api/push_to_anx/${id}`, { method: 'POST' })
                    .then(res => {
                        if (!res.ok) return res.json().then(err => { throw new Error(err.error) });
                        return res.json();
                    });
                handleButtonAnimation(target, apiCall);
                break;
            }
            case 'send-kindle': {
                const apiCall = fetch_with_token(`/api/send_to_kindle/${id}`, { method: 'POST' })
                    .then(async res => {
                        if (!res.ok) {
                            const err = await res.json();
                            const error = new Error(err.error);
                            error.status = res.status;
                            throw error;
                        }
                        return res.json();
                    });
                handleButtonAnimation(target, apiCall);
                break;
            }
            case 'save-changes':
                handleSaveChanges(target, editBookForm, currentEditing, anxBooksData, calibreBooksData, editModal);
                break;
            case 'download-anx':
                window.location.href = `/api/download_anx_book/${id}`;
                break;
            case 'download-calibre':
                window.location.href = `/api/download_book/${id}`;
                break;
            case 'jump-to-page': {
                const pageInput = document.getElementById('page-jump-input');
                const totalPages = parseInt(document.querySelector('.pagination-controls').dataset.totalPages, 10);
                const page = parseInt(pageInput.value, 10);
                if (page && page > 0 && page <= totalPages) {
                    const url = new URL(window.location.href);
                    url.searchParams.set('page', page);
                    showLoaderAndNavigate(url.href, calibreLoader);
                } else {
                    alert(t.invalidPageNumber.replace('%(totalPages)s', totalPages));
                }
                break;
            }
            case 'jump-to-page-bottom': {
                const pageInput = document.getElementById('page-jump-input-bottom');
                const totalPages = parseInt(document.querySelector('.pagination-controls').dataset.totalPages, 10);
                const page = parseInt(pageInput.value, 10);
                if (page && page > 0 && page <= totalPages) {
                    const url = new URL(window.location.href);
                    url.searchParams.set('page', page);
                    showLoaderAndNavigate(url.href, calibreLoader);
                } else {
                    alert(t.invalidPageNumber.replace('%(totalPages)s', totalPages));
                }
                break;
            }
            case 'go-home':
                showLoaderAndNavigate("/", calibreLoader);
                break;
            case 'toggle-fullscreen': {
                const container = target.closest('.textarea-container');
                if (container) {
                    const icon = target.querySelector('i');
                    const isMobile = window.innerWidth <= 768;
                    const fullscreenClass = isMobile ? 'fullscreen-mobile' : 'fullscreen-desktop';

                    container.classList.toggle(fullscreenClass);
                    
                    if (container.classList.contains(fullscreenClass)) {
                        icon.classList.remove('fa-expand');
                        icon.classList.add('fa-compress');
                    } else {
                        icon.classList.remove('fa-compress');
                        icon.classList.add('fa-expand');
                    }
                }
                break;
            }
            default:
            // Let navigation handlers take care of the rest
        }
    });

    document.getElementById('uploadForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        const files = Array.from(document.getElementById('book-upload-input').files);
        const progressContainer = document.getElementById('upload-progress-container');
        progressContainer.innerHTML = ''; // Clear previous results

        if (files.length === 0) {
            alert(t.selectFilesToUpload);
            return;
        }

        // --- Step 1: Create all UI elements first ---
        const progressElements = files.map(file => {
            const progressWrapper = document.createElement('div');
            progressWrapper.className = 'progress-wrapper';
            const fileNameSpan = document.createElement('span');
            fileNameSpan.textContent = file.name;
            const progressBar = document.createElement('progress');
            progressBar.max = 100;
            progressBar.value = 0;
            const progressLabel = document.createElement('span');
            progressLabel.textContent = t.waiting; // Set initial state to Waiting
            progressWrapper.appendChild(fileNameSpan);
            progressWrapper.appendChild(progressBar);
            progressWrapper.appendChild(progressLabel);
            progressContainer.appendChild(progressWrapper);
            return { wrapper: progressWrapper, bar: progressBar, label: progressLabel };
        });

        // --- Step 2: Process files sequentially ---
        let all_successful = true;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const { wrapper, bar, label } = progressElements[i];
            
            label.textContent = t.uploading; // Update status before starting

            const success = await new Promise((resolve) => {
                const formData = new FormData();
                formData.append('books', file);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', "/api/upload_to_calibre", true);

                xhr.upload.onprogress = function(event) {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        bar.value = percentComplete;
                        if (percentComplete >= 100) {
                            label.textContent = t.processing;
                        } else {
                            label.textContent = Math.round(percentComplete) + '%';
                        }
                    }
                };

                xhr.onload = function() {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        const results = JSON.parse(xhr.responseText);
                        const result = results[0];
                        if (result.success) {
                            label.textContent = '✅ ' + result.message;
                            wrapper.classList.add('success');
                            resolve(true);
                        } else {
                            label.textContent = '❌ ' + result.error;
                            wrapper.classList.add('error');
                            resolve(false);
                        }
                    } else {
                        label.textContent = `❌ ${t.uploadFailed}: ${xhr.statusText}`;
                        wrapper.classList.add('error');
                        resolve(false);
                    }
                };

                xhr.onerror = function() {
                    label.textContent = `❌ ${t.networkError}.`;
                    wrapper.classList.add('error');
                    resolve(false);
                };

                xhr.send(formData);
            });

            if (!success) {
                all_successful = false;
            }
        }

        // --- Step 3: Final notification ---
        if (all_successful) {
            alert(t.allBooksUploaded);
        } else {
            alert(t.someFilesFailedUpload);
        }
        
        // Reload the page after user confirms the alert, regardless of success or failure
        setTimeout(() => {
            location.reload();
        }, 500);
    });

    document.querySelector('.search-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const url = new URL(this.action);
        url.searchParams.set('search', this.elements.search.value);
        url.searchParams.set('page_size', document.querySelector('.pagination-form select[name="page_size"]').value);
        url.searchParams.set('page', 1); // Reset to page 1 on new search
        showLoaderAndNavigate(url.href, calibreLoader);
    });

    document.querySelectorAll('.pagination-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            showLoaderAndNavigate(this.href, calibreLoader);
        });
    });

    document.querySelectorAll('.pagination-form select[name="page_size"]').forEach(select => {
        select.addEventListener('change', function() {
            const url = new URL(window.location.href);
            url.searchParams.set('page_size', this.value);
            url.searchParams.set('page', 1); // Reset to page 1 on size change
            showLoaderAndNavigate(url.href, calibreLoader);
        });
    });

    // Initialize audiobook buttons after all other handlers are set up
    initializeAudiobookButtons();
}