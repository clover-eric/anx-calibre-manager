import { fetch_with_token, showModal, hideModal, showLoaderAndNavigate } from './utils.js';
import { populateAnxEditForm, populateCalibreEditForm, handleButtonAnimation } from './ui.js';

function handleSaveChanges(saveButton, editBookForm, currentEditing, anxBooksData, calibreBooksData, editModal) {
    const formData = new FormData(editBookForm);
    const currentData = Object.fromEntries(formData.entries());
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
         alert('没有检测到任何更改。');
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
                if (confirm('确定要删除这本书吗？此操作不可恢复。')) {
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
                    alert(`请输入一个介于 1 和 ${totalPages} 之间的有效页码。`);
                }
                break;
            }
            case 'go-home':
                showLoaderAndNavigate("/", calibreLoader);
                break;
            default:
            // Let navigation handlers take care of the rest
        }
    });

    document.getElementById('uploadForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const files = document.getElementById('book-upload-input').files;
        const progressContainer = document.getElementById('upload-progress-container');
        progressContainer.innerHTML = ''; // Clear previous results

        if (files.length === 0) {
            alert('请选择要上传的文件。');
            return;
        }

        const uploadPromises = Array.from(files).map(file => {
            return new Promise((resolve, reject) => {
                const formData = new FormData();
                formData.append('books', file);

                const progressWrapper = document.createElement('div');
                progressWrapper.className = 'progress-wrapper';
                const fileNameSpan = document.createElement('span');
                fileNameSpan.textContent = file.name;
                const progressBar = document.createElement('progress');
                progressBar.max = 100;
                progressBar.value = 0;
                const progressLabel = document.createElement('span');
                progressLabel.textContent = '0%';
                progressWrapper.appendChild(fileNameSpan);
                progressWrapper.appendChild(progressBar);
                progressWrapper.appendChild(progressLabel);
                progressContainer.appendChild(progressWrapper);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', "/api/upload_to_calibre", true);

                xhr.upload.onprogress = function(event) {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        progressBar.value = percentComplete;
                        if (percentComplete >= 100) {
                            progressLabel.textContent = '处理中...';
                        } else {
                            progressLabel.textContent = Math.round(percentComplete) + '%';
                        }
                    }
                };

                xhr.onload = function() {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        const results = JSON.parse(xhr.responseText);
                        const result = results[0];
                        if (result.success) {
                            progressLabel.textContent = '✅ ' + result.message;
                            progressWrapper.classList.add('success');
                            resolve(true);
                        } else {
                            progressLabel.textContent = '❌ ' + result.error;
                            progressWrapper.classList.add('error');
                            resolve(false);
                        }
                    } else {
                        progressLabel.textContent = `❌ 上传失败: ${xhr.statusText}`;
                        progressWrapper.classList.add('error');
                        reject(new Error(xhr.statusText));
                    }
                };

                xhr.onerror = function() {
                    progressLabel.textContent = '❌ 网络错误。';
                    progressWrapper.classList.add('error');
                    reject(new Error("Network Error"));
                };

                xhr.send(formData);
            });
        });

        Promise.all(uploadPromises).then(results => {
            if (results.every(r => r === true)) {
                setTimeout(() => {
                    alert('所有书籍上传成功！');
                    location.reload();
                }, 1000);
            }
        }).catch(error => {
            console.error("An error occurred during upload:", error);
        });
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

    document.querySelector('.pagination-form select[name="page_size"]').addEventListener('change', function() {
        const url = new URL(window.location.href);
        url.searchParams.set('page_size', this.value);
        url.searchParams.set('page', 1); // Reset to page 1 on size change
        showLoaderAndNavigate(url.href, calibreLoader);
    });
}