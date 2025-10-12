import { t, initializeTranslations } from './translations.js';

document.addEventListener('DOMContentLoaded', () => {
    initializeTranslations();

    // --- Mermaid Initialization with Theme ---
    if (window.mermaid) {
        const bodyClass = document.body.className;
        let mermaidTheme = 'default';
        if (bodyClass.includes('theme-dark')) {
            mermaidTheme = 'dark';
        } else if (bodyClass.includes('theme-auto') && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            mermaidTheme = 'dark';
        }
        
        window.mermaid.initialize({
            startOnLoad: false,
            theme: mermaidTheme,
        });
    }

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
        menuToggleBtn: document.querySelector('.menu-toggle-btn'),
        menuDropdown: document.querySelector('.menu-dropdown'),
        exportChatBtn: document.getElementById('export-chat-btn'),
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

    const streamAndRenderResponse = async (response, modelMessageWrapper, userMessageWrapper = null) => {
        const modelMessageContent = modelMessageWrapper.querySelector('.message-content');
        if (!modelMessageContent) {
            console.error("Could not find message content element to stream response.");
            return;
        }
        modelMessageContent.innerHTML = `
            <div class="loading-indicator">
                <div class="spinner"></div>
                <span class="loading-status"></span>
            </div>
        `;
        let fullResponse = '';
        let buffer = '';

        try {
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
                buffer = lines.pop();

                for (const block of lines) {
                    const eventMatch = block.match(/^event: (.*)$/m);
                    const dataMatch = block.match(/^data: (.*)$/m);

                    if (eventMatch) {
                        const eventType = eventMatch[1];
                        const dataStr = dataMatch ? dataMatch[1] : '{}';
                        const data = JSON.parse(dataStr);

                        if (eventType === 'session_start') {
                            const isNewSession = !currentSession.sessionId;
                            currentSession.sessionId = data.session_id;
                            if (isNewSession) addSessionToListUI(currentSession);

                            if (data.user_message_id && userMessageWrapper) {
                                if (!userMessageWrapper.dataset.messageId) {
                                    userMessageWrapper.dataset.messageId = data.user_message_id;
                                    
                                    const regenerateBtn = userMessageWrapper.querySelector('.regenerate-btn');
                                    const deleteBtn = userMessageWrapper.querySelector('.delete-btn');
                                    
                                    if (regenerateBtn) regenerateBtn.disabled = false;
                                    if (deleteBtn) deleteBtn.disabled = false;
                                }
                            }
                        } else if (eventType === 'stage_update') {
                            const statusSpan = modelMessageWrapper.querySelector('.loading-status');
                            if (statusSpan) {
                                statusSpan.textContent = data.message;
                            }
                        } else if (eventType === 'end') {
                            const sessionItem = document.querySelector(`.session-item[data-session-id="${currentSession.sessionId}"]`);
                            if (sessionItem) {
                                const timeAgoEl = sessionItem.querySelector('.time-ago');
                                if (timeAgoEl) {
                                    timeAgoEl.textContent = t.justNow;
                                    timeAgoEl.dataset.timestamp = new Date().toISOString().slice(0, 19).replace('T', ' ');
                                }
                            }
                            
                            if (data.model_message_id && modelMessageWrapper) {
                                modelMessageWrapper.dataset.messageId = data.model_message_id;
                                const actionsContainer = modelMessageWrapper.querySelector('.message-actions');
                                if (actionsContainer) {
                                    const deleteButton = createActionButton(t.delete, 'fa-trash-alt', 'delete-btn', () => deleteMessageHandler(modelMessageWrapper));
                                    actionsContainer.appendChild(deleteButton);
                                }
                            }
                            return;
                        } else if (eventType === 'error') {
                            throw new Error(data.error || t.anErrorOccurred);
                        }
                    } else if (dataMatch) {
                        if (!firstChunkReceived) {
                            modelMessageContent.innerHTML = '';
                            firstChunkReceived = true;
                        }
                        const data = JSON.parse(dataMatch[1]);
                        if (data.chunk) {
                            fullResponse += data.chunk;
                            modelMessageContent.innerHTML = marked.parse(fullResponse);
                            renderMermaid(modelMessageContent);
                            dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
                        }
                    }
                }
            }
        } catch (error) {
            console.error(error);
            modelMessageContent.innerHTML = marked.parse(`${t.anErrorOccurred} ${error.message}`);
        }
    };

    const handleRegenerate = async (messageWrapper) => {
        const messageId = messageWrapper.dataset.messageId;
        if (!messageId) return;

        let nextSibling = messageWrapper.nextElementSibling;
        while (nextSibling) {
            const toRemove = nextSibling;
            nextSibling = nextSibling.nextElementSibling;
            toRemove.remove();
        }

        dom.sendButton.disabled = true;
        const modelMessageWrapper = addMessageToUI({ role: 'model', content: '' });

        try {
            const response = await fetch('/api/llm/regenerate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_id: parseInt(messageId) }),
            });
            await streamAndRenderResponse(response, modelMessageWrapper);
        } catch (error) {
            console.error('Regeneration fetch failed:', error);
            const contentEl = modelMessageWrapper.querySelector('.message-content');
            if (contentEl) contentEl.innerHTML = marked.parse(`${t.anErrorOccurred} ${error.message}`);
        } finally {
            dom.sendButton.disabled = false;
        }
    };

    const sendMessage = async (message) => {
        if (!currentSession.bookId || !message.trim()) return;

        const userMessageWrapper = addMessageToUI({ role: 'user', content: message });
        dom.chatInput.value = '';
        autoResizeTextarea();
        dom.sendButton.disabled = true;

        const modelMessageWrapper = addMessageToUI({ role: 'model', content: '' });

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
            await streamAndRenderResponse(response, modelMessageWrapper, userMessageWrapper);
        } catch (error) {
            console.error('Send message fetch failed:', error);
            const contentEl = modelMessageWrapper.querySelector('.message-content');
            if (contentEl) contentEl.innerHTML = marked.parse(`${t.anErrorOccurred} ${error.message}`);
        } finally {
            dom.sendButton.disabled = false;
        }
    };

    // --- Helper functions for creating UI elements ---
    const createActionButton = (title, iconClass, btnClass, onClick) => {
        const button = document.createElement('button');
        button.title = title;
        button.innerHTML = `<i class="fas ${iconClass}"></i>`;
        button.classList.add(btnClass);
        button.addEventListener('click', onClick);
        return button;
    };

    const copyMessageHandler = (messageWrapper) => {
        const textToCopy = messageWrapper.querySelector('.message-content').textContent;
        const copyButton = messageWrapper.querySelector('.copy-btn');
        const icon = copyButton.querySelector('i');

        const copySuccess = () => {
            icon.classList.remove('fa-copy');
            icon.classList.add('fa-check');
            copyButton.title = t.copied;
            setTimeout(() => {
                icon.classList.remove('fa-check');
                icon.classList.add('fa-copy');
                copyButton.title = t.copy;
            }, 1500);
        };

        const fallbackCopy = () => {
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            textArea.style.position = 'fixed';
            textArea.style.top = '-9999px';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                if (document.execCommand('copy')) {
                    copySuccess();
                } else {
                    throw new Error('Copy command was not successful');
                }
            } catch (err) {
                console.error('Fallback copy failed:', err);
                alert(t.copyFailed);
            }
            document.body.removeChild(textArea);
        };

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(textToCopy).then(copySuccess).catch((err) => {
                console.warn('Clipboard API failed, trying fallback:', err);
                fallbackCopy();
            });
        } else {
            fallbackCopy();
        }
    };

    const deleteMessageHandler = async (messageWrapper) => {
        const messageId = messageWrapper.dataset.messageId;
        if (!messageId) return;

        try {
            const response = await fetch(`/api/llm/message/${messageId}`, { method: 'DELETE' });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || t.failedToDeleteMessage);
            }
            messageWrapper.remove();
        } catch (error) {
            console.error('Error deleting message:', error);
        }
    };


    // --- Render & UI Logic ---
    const addMessageToUI = (message, isHtml = false, messageId = null) => {
        const messageWrapper = document.createElement('div');
        messageWrapper.classList.add('message', message.role);
        if (messageId) {
            messageWrapper.dataset.messageId = messageId;
        }
        
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');

        if (isHtml) {
            messageContent.innerHTML = message.content;
        } else if (message.role === 'model') {
            messageContent.innerHTML = marked.parse(message.content || '');
            renderMermaid(messageContent);
        } else {
            messageContent.textContent = message.content;
        }

        if (message.role === 'model' && message.content.includes('spinner')) {
            messageWrapper.classList.add('loading');
        }
        
        const actionsContainer = document.createElement('div');
        actionsContainer.classList.add('message-actions');
        
        const copyButton = createActionButton(t.copy, 'fa-copy', 'copy-btn', () => copyMessageHandler(messageWrapper));
        actionsContainer.appendChild(copyButton);

        if (message.role === 'user') {
            const regenerateButton = createActionButton(t.regenerate || 'Regenerate', 'fa-sync-alt', 'regenerate-btn', () => handleRegenerate(messageWrapper));
            const deleteButton = createActionButton(t.delete, 'fa-trash-alt', 'delete-btn', () => deleteMessageHandler(messageWrapper));
            
            if (!messageId) {
                regenerateButton.disabled = true;
                deleteButton.disabled = true;
            }
            
            actionsContainer.appendChild(regenerateButton);
            actionsContainer.appendChild(deleteButton);
        }

        if (message.role === 'model' && messageId) {
            const deleteButton = createActionButton(t.delete, 'fa-trash-alt', 'delete-btn', () => deleteMessageHandler(messageWrapper));
            actionsContainer.appendChild(deleteButton);
        }
        
        messageWrapper.appendChild(messageContent);
        messageWrapper.appendChild(actionsContainer);

        dom.messagesContainer.appendChild(messageWrapper);
        dom.messagesContainer.scrollTop = dom.messagesContainer.scrollHeight;
        return messageWrapper;
    };

    const addSessionToListUI = (session) => {
        const listId = `${session.bookType}-list`;
        const listEl = document.getElementById(listId);
        if (!listEl) return;

        // Remove placeholder if it exists
        const placeholder = listEl.querySelector('.empty-list-message');
        if (placeholder) {
            placeholder.remove();
        }

        // Create the new session item element
        const newItem = document.createElement('div');
        newItem.className = 'session-item';
        newItem.dataset.bookId = session.bookId;
        newItem.dataset.bookType = session.bookType;
        newItem.dataset.bookTitle = session.bookTitle;
        newItem.dataset.sessionId = session.sessionId;

        newItem.innerHTML = `
            <div class="session-info">
                <h4 class="marquee"><span>${session.bookTitle}</span></h4>
                <p>${t.updated} <span class="time-ago" data-timestamp="${new Date().toISOString().slice(0, 19).replace('T', ' ')}">${t.justNow}</span></p>
            </div>
            <button class="delete-session-btn" title="${t.deleteChat}">
                <i class="fas fa-trash-alt"></i>
            </button>
        `;

        // Add event listeners
        newItem.addEventListener('click', () => handleSessionClick(newItem));
        newItem.querySelector('.delete-session-btn').addEventListener('click', handleDeleteSession);

        // Add to list and update dom.sessionItems
        listEl.prepend(newItem);
        dom.sessionItems = document.querySelectorAll('.session-item'); // Refresh the list

        // Update tab count robustly
        const tabButton = document.querySelector(`.library-toggle .button[data-library="${session.bookType}"]`);
        if (tabButton) {
            const countMatch = tabButton.textContent.match(/\((\d+)\)/);
            const currentCount = countMatch ? parseInt(countMatch[1], 10) : 0;
            const baseText = tabButton.textContent.replace(/\s*\(\d+\)/, '').trim();
            tabButton.textContent = `${baseText} (${currentCount + 1})`;
        }
        
        updateActiveItem(newItem);
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
            history.messages.forEach(msg => addMessageToUI({ role: msg.role, content: msg.content }, false, msg.id));
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

    const renderMermaid = async (container) => {
        const mermaidBlocks = container.querySelectorAll('pre code.language-mermaid');
        for (const block of mermaidBlocks) {
            const pre = block.parentNode;
            // Use innerText instead of textContent to correctly handle line breaks (<br>)
            // that marked.js might insert. innerText preserves the line breaks.
            let originalContent = block.innerText;

            const wrapper = document.createElement('div');
            wrapper.className = 'mermaid-wrapper';

            const controls = document.createElement('div');
            controls.className = 'mermaid-controls';
            controls.innerHTML = `
                <button data-action="zoom-in" title="${t.zoomIn || 'Zoom In'}"><i class="fas fa-plus"></i></button>
                <button data-action="zoom-out" title="${t.zoomOut || 'Zoom Out'}"><i class="fas fa-minus"></i></button>
                <button data-action="reset" title="${t.resetZoom || 'Reset'}"><i class="fas fa-expand"></i></button>
                <button data-action="download" title="${t.downloadSVG || 'Download SVG'}"><i class="fas fa-download"></i></button>
            `;

            const mermaidContainer = document.createElement('div');
            mermaidContainer.className = 'mermaid';
            mermaidContainer.textContent = originalContent;

            wrapper.appendChild(controls);
            wrapper.appendChild(mermaidContainer);
            pre.parentNode.replaceChild(wrapper, pre);

            try {
                await window.mermaid.run({ nodes: [mermaidContainer] });
                const svgElement = mermaidContainer.querySelector('svg');
                
                if (svgElement) {
                    const panZoomInstance = svgPanZoom(svgElement, {
                        zoomEnabled: true,
                        controlIconsEnabled: false,
                        fit: true,
                        center: true,
                        minZoom: 0.1,
                        maxZoom: 50,
                        touchEnabled: true,
                        dblClickZoomEnabled: true,
                        mouseWheelZoomEnabled: true, // Enable mouse wheel zoom
                        preventMouseEventsDefault: true, // Prevent page scroll while zooming/panning
                        zoomScaleSensitivity: 0.3, // Adjust zoom sensitivity
                    });

                    controls.addEventListener('click', (e) => {
                        const button = e.target.closest('button');
                        if (!button) return;
                        const action = button.dataset.action;

                        if (action === 'zoom-in') {
                            panZoomInstance.zoomIn();
                        } else if (action === 'zoom-out') {
                            panZoomInstance.zoomOut();
                        } else if (action === 'reset') {
                            panZoomInstance.resetZoom();
                        } else if (action === 'download') {
                            const svgData = new XMLSerializer().serializeToString(svgElement);
                            const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = 'mermaid-diagram.svg';
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                        }
                    });
                }

            } catch (e) {
                console.error("Mermaid rendering error:", e);
                wrapper.innerHTML = `<p class="error">${t.mermaidRenderError || 'Mermaid Render Error'}</p><pre><code>${originalContent}</code></pre>`;
            }
        }
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

    dom.menuToggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        dom.menuDropdown.classList.toggle('visible');
    });

    document.addEventListener('click', (e) => {
        if (!dom.menuDropdown.contains(e.target) && !dom.menuToggleBtn.contains(e.target)) {
            dom.menuDropdown.classList.remove('visible');
        }
    });

    dom.exportChatBtn.addEventListener('click', () => {
        dom.menuDropdown.classList.remove('visible');
        const chatTitle = dom.chatTitle.textContent || 'chat';
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
        const filename = `${chatTitle}_${timestamp}.png`;

        const exportContainer = document.createElement('div');
        exportContainer.className = 'export-container';

        const header = document.createElement('div');
        header.className = 'export-header';
        header.textContent = chatTitle;
        exportContainer.appendChild(header);

        const contentToCapture = dom.messagesContainer.cloneNode(true);
        exportContainer.appendChild(contentToCapture);

        const footer = document.createElement('div');
        footer.className = 'export-footer';
        footer.innerHTML = `
            <p>${t.exportedBy}</p>
            <p>${t.aiDisclaimer}</p>
        `;
        exportContainer.appendChild(footer);

        document.body.appendChild(exportContainer);

        const style = document.createElement('style');
        style.innerHTML = `.message:hover .message-actions { visibility: hidden !important; }`;
        document.head.appendChild(style);

        html2canvas(exportContainer, {
            useCORS: true,
            backgroundColor: getComputedStyle(dom.body).getPropertyValue('--background-color'),
            onclone: (clonedDoc) => {
                clonedDoc.querySelectorAll('.mermaid svg').forEach(svg => {
                    const styleSheets = Array.from(clonedDoc.styleSheets);
                    let cssText = '';
                    styleSheets.forEach(sheet => {
                        try {
                            Array.from(sheet.cssRules).forEach(rule => { cssText += rule.cssText; });
                        } catch (e) { console.warn("Cannot access stylesheet rules:", e); }
                    });
                    const styleEl = clonedDoc.createElement('style');
                    styleEl.textContent = cssText;
                    svg.insertBefore(styleEl, svg.firstChild);
                });
            }
        }).then(canvas => {
            const link = document.createElement('a');
            link.download = filename;
            link.href = canvas.toDataURL('image/png');
            link.click();
        }).finally(() => {
            document.head.removeChild(style);
            document.body.removeChild(exportContainer);
        });
    });

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