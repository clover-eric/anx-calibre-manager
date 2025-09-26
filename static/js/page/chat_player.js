import { t, initializeTranslations } from './translations.js';

document.addEventListener('DOMContentLoaded', () => {
    initializeTranslations();

    // --- State ---
    let currentSession = { bookId: null, bookType: null, bookTitle: null, sessionId: null };
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    // --- DOM Elements ---
    const dom = {
        body: document.body,
        libraryToggleButtons: document.querySelectorAll('.library-toggle .button'),
        sessionLists: document.querySelectorAll('.session-list'),
        sessionItems: document.querySelectorAll('.session-item'),
        detailView: document.querySelector('.detail-view'),
        placeholderView: document.querySelector('.placeholder-view'),
        chatContentView: document.querySelector('.chat-content-view'),
        chatTitle: document.querySelector('.chat-title span'),
        backToListBtn: document.querySelector('.back-to-list-btn'),
        messagesContainer: document.querySelector('.messages-container'),
        chatInput: document.getElementById('chat-input'),
        sendButton: document.getElementById('send-button'),
    };

    // --- API Functions ---
    const fetchChatHistory = async (bookId, bookType) => {
        try {
            const response = await fetch(`/api/llm/history?book_id=${bookId}&book_type=${bookType}`);
            if (!response.ok) {
                if (response.status === 404) return { messages: [], session_id: null };
                const errorData = await response.json();
                throw new Error(errorData.error || t.failedToFetchChatHistory);
            }
            return await response.json();
        } catch (error) {
            console.error(error);
            addMessageToUI({ role: 'model', content: `${t.errorLoadingHistory} ${error.message}` });
            return { messages: [], session_id: null };
        }
    };

    const sendMessage = async (message) => {
        if (!currentSession.bookId || !message.trim()) return;

        addMessageToUI({ role: 'user', content: message });
        dom.chatInput.value = '';
        autoResizeTextarea();
        dom.sendButton.disabled = true;

        const modelMessageElement = addMessageToUI({ role: 'model', content: '' });
        modelMessageElement.innerHTML = '<div class="spinner"></div>'; // Show spinner initially
        let fullResponse = '';
        let buffer = '';

        try {
            const response = await fetch('/api/llm/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSession.sessionId,
                    book_id: currentSession.bookId,
                    book_type: currentSession.bookType,
                    book_title: currentSession.bookTitle,
                    message: message,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || t.failedToGetResponse);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let firstChunkReceived = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep the last (potentially incomplete) message in buffer

                for (const block of lines) {
                    const eventMatch = block.match(/^event: (.*)$/m);
                    const dataMatch = block.match(/^data: (.*)$/m);

                    if (eventMatch) {
                        const eventType = eventMatch[1];
                        const dataStr = dataMatch ? dataMatch[1] : '{}';
                        const data = JSON.parse(dataStr);

                        if (eventType === 'session_start') {
                            currentSession.sessionId = data.session_id;
                        } else if (eventType === 'end') {
                            return; // Stream finished
                        } else if (eventType === 'error') {
                            throw new Error(data.error || t.anErrorOccurred);
                        }
                    } else if (dataMatch) {
                        if (!firstChunkReceived) {
                            modelMessageElement.innerHTML = ''; // Clear spinner
                            firstChunkReceived = true;
                        }
                        const data = JSON.parse(dataMatch[1]);
                        if (data.chunk) {
                            fullResponse += data.chunk;
                            modelMessageElement.innerHTML = marked.parse(fullResponse);
                            dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
                        }
                    }
                }
            }
        } catch (error) {
            console.error(error);
            modelMessageElement.innerHTML = marked.parse(`${t.anErrorOccurred} ${error.message}`);
        } finally {
            dom.sendButton.disabled = false;
        }
    };

    // --- Render & UI Logic ---
    const addMessageToUI = (message, isHtml = false) => {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', message.role);

        if (isHtml) { // Used for the loading spinner
            messageElement.innerHTML = message.content;
        } else if (message.role === 'model') {
            // Use marked to render Markdown for model responses
            // Note: For production, consider a sanitizer like DOMPurify if the source isn't fully trusted.
            messageElement.innerHTML = marked.parse(message.content || '');
        } else { // 'user' role
            // Use textContent for user messages to prevent XSS
            messageElement.textContent = message.content;
        }

        if (message.role === 'model' && message.content.includes('spinner')) {
            messageElement.classList.add('loading');
        }
        
        dom.messagesContainer.appendChild(messageElement);
        dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
        return messageElement;
    };

    const handleSessionClick = async (item) => {
        const { bookId, bookType, bookTitle } = item.dataset;
        currentSession = { bookId: parseInt(bookId), bookType, bookTitle, sessionId: null };

        updateActiveItem(item);
        dom.placeholderView.classList.add('hidden');
        dom.chatTitle.textContent = bookTitle;
        dom.chatContentView.classList.remove('hidden');
        
        if (isMobile) {
            dom.detailView.classList.add('mobile-visible');
        }

        dom.messagesContainer.innerHTML = '<div class="spinner"></div>';
        const history = await fetchChatHistory(bookId, bookType);
        currentSession.sessionId = history.session_id;
        
        dom.messagesContainer.innerHTML = '';
        if (history.messages && history.messages.length > 0) {
            history.messages.forEach(msg => addMessageToUI(msg));
        } else {
            const initialPrompt = t.initialChatPrompt;
            sendMessage(initialPrompt);
        }
    };

    const updateActiveItem = (activeItem) => {
        dom.sessionItems.forEach(item => item.classList.remove('active'));
        if (activeItem) activeItem.classList.add('active');
    };

    const initTabs = () => {
        const activeLibrary = dom.body.dataset.activeLibrary || 'calibre';
        const showTab = (libraryId) => {
            dom.libraryToggleButtons.forEach(btn => btn.classList.toggle('active', btn.dataset.library === libraryId));
            dom.sessionLists.forEach(list => list.classList.toggle('active', list.id === `${libraryId}-list`));
        };
        dom.libraryToggleButtons.forEach(button => {
            button.addEventListener('click', () => showTab(button.dataset.library));
        });
        showTab(activeLibrary);
    };

    const autoResizeTextarea = () => {
        dom.chatInput.style.height = 'auto';
        dom.chatInput.style.height = `${dom.chatInput.scrollHeight}px`;
    };

    const initTimeAgo = () => {
        document.querySelectorAll('.time-ago').forEach(span => {
            const timestamp = span.dataset.timestamp;
            if (!timestamp) return;
            const date = new Date(timestamp.replace(' ', 'T') + 'Z');
            const now = new Date();
            const seconds = Math.floor((now - date) / 1000);
            let interval = seconds / 31536000;
            if (interval > 1) { span.textContent = `${Math.floor(interval)} ${t.yearsAgo}`; return; }
            interval = seconds / 2592000;
            if (interval > 1) { span.textContent = `${Math.floor(interval)} ${t.monthsAgo}`; return; }
            interval = seconds / 86400;
            if (interval > 1) { span.textContent = `${Math.floor(interval)} ${t.daysAgo}`; return; }
            interval = seconds / 3600;
            if (interval > 1) { span.textContent = `${Math.floor(interval)} ${t.hoursAgo}`; return; }
            interval = seconds / 60;
            if (interval > 1) { span.textContent = `${Math.floor(interval)} ${t.minutesAgo}`; return; }
            span.textContent = t.justNow;
        });
    };

    const handleDeleteSession = async (e) => {
        e.stopPropagation(); // Prevent triggering the session click event
        const button = e.currentTarget;
        const item = button.closest('.session-item');
        const sessionId = item.dataset.sessionId;

        if (!confirm(t.confirmDeleteChat)) {
            return;
        }

        try {
            const response = await fetch(`/api/llm/session/${sessionId}`, { method: 'DELETE' });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || t.failedToDeleteSession);
            }

            // If the deleted session was the active one, reset the detail view
            if (currentSession.sessionId === sessionId) {
                dom.chatContentView.classList.add('hidden');
                dom.placeholderView.classList.remove('hidden');
                currentSession = { bookId: null, bookType: null, bookTitle: null, sessionId: null };
            }
            
            item.remove();
            // Optionally, update the count in the tab button
            // This is a simple implementation. A more robust one might re-fetch counts.
            const tabButton = document.querySelector(`.library-toggle .button[data-library="${item.dataset.bookType}"]`);
            if(tabButton) {
                const count = parseInt(tabButton.textContent.match(/\((\d+)\)/)[1], 10);
                tabButton.textContent = tabButton.textContent.replace(`(${count})`, `(${count - 1})`);
            }

        } catch (error) {
            alert(`${t.errorLabel} ${error.message}`);
        }
    };

    // --- Event Listeners ---
    dom.sessionItems.forEach(item => {
        item.addEventListener('click', () => handleSessionClick(item));
        const deleteBtn = item.querySelector('.delete-session-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', handleDeleteSession);
        }
    });
    dom.backToListBtn.addEventListener('click', () => dom.detailView.classList.remove('mobile-visible'));
    dom.sendButton.addEventListener('click', () => sendMessage(dom.chatInput.value));
    dom.chatInput.addEventListener('keydown', (e) => {
        // On desktop, allow Shift+Enter for newline, and Enter to send.
        // On mobile, this listener does nothing, allowing the virtual keyboard's
        // Enter key to function as a standard newline character.
        if (!isMobile && e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage(dom.chatInput.value);
        }
    });
    dom.chatInput.addEventListener('input', autoResizeTextarea);

    // --- Initial Load ---
    initTabs();
    initTimeAgo();
    autoResizeTextarea();

    const initialBookId = dom.body.dataset.initialBookId;
    if (initialBookId) {
        const itemToLoad = document.querySelector(`.session-item[data-book-id='${initialBookId}']`);
        if (itemToLoad) {
            handleSessionClick(itemToLoad);
        } else {
            const { initialBookType, initialBookTitle } = dom.body.dataset;
            currentSession = { bookId: parseInt(initialBookId), bookType: initialBookType, bookTitle: initialBookTitle, sessionId: null };
            updateActiveItem(null);
            dom.placeholderView.classList.add('hidden');
            dom.chatTitle.textContent = initialBookTitle;
            dom.chatContentView.classList.remove('hidden');
            if (isMobile) {
                dom.detailView.classList.add('mobile-visible');
            }
            const initialPrompt = t.initialChatPrompt;
            sendMessage(initialPrompt);
        }
    }
});