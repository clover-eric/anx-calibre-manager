import './foliate/view.js';
import { createTOCView } from './foliate/ui/tree.js';

// --- Utility Functions ---
const debounce = (func, delay) => {
    let timeoutId;
    return (...args) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
};

// --- Translatable Strings ---
const t = {
    failedToFetchSettings: _('Failed to fetch user settings'),
    invalidBookType: _('Invalid book type specified.'),
    invalidUrl: _('Invalid URL for book reader.'),
    failedToFetchBook: _('Failed to fetch book: {statusText}'),
    failedToInitRenderer: _('Failed to initialize book renderer.'),
    errorLoadingBook: _('Error loading book: {message}'),
    untitled: _('Untitled'),
    unknownAuthor: _('Unknown Author'),
    noVoices: _('No voices available')
};

document.addEventListener('DOMContentLoaded', () => {
    const readerContainer = document.getElementById('reader-container');
    const loadingOverlay = document.getElementById('loading-overlay');
    const urlPath = window.location.pathname;
    const pathParts = urlPath.split('/');

    // UI Elements
    const leftButton = document.getElementById('left-button');
    const rightButton = document.getElementById('right-button');
    const sidebarButton = document.getElementById('side-bar-button');
    const ttsButton = document.getElementById('tts-button');
    const dimmingOverlay = document.getElementById('dimming-overlay');
    const sideBar = document.getElementById('side-bar');
    const progressSlider = document.getElementById('progress-slider');
    const progressLabel = document.getElementById('progress-label');
    const sideBarTitle = document.getElementById('side-bar-title');
    const sideBarAuthor = document.getElementById('side-bar-author');
    const sideBarCover = document.getElementById('side-bar-cover');
    const tocViewContainer = document.getElementById('toc-view');
    const headerTitle = document.getElementById('header-title');
    const ttsSettingsButton = document.getElementById('tts-settings-button');
    const ttsPopover = document.getElementById('tts-settings-popover');
    const ttsRate = document.getElementById('tts-rate');
    const ttsRateLabel = document.getElementById('tts-rate-label');
    const ttsPitch = document.getElementById('tts-pitch');
    const ttsPitchLabel = document.getElementById('tts-pitch-label');
    const ttsVoice = document.getElementById('tts-voice');

    // Helper functions for loading animation
    function showLoading() {
        if (loadingOverlay) loadingOverlay.classList.remove('hidden');
    }

    function hideLoading() {
        if (loadingOverlay) loadingOverlay.classList.add('hidden');
    }

    // Theme setup
    const getCSS = ({ spacing = 1.4, justify = true, hyphenate = true } = {}) => `
        @namespace epub "http://www.idpf.org/2007/ops";
        html {
            color-scheme: light dark;
        }
        @media (prefers-color-scheme: dark) {
            a:link {
                color: lightblue;
            }
        }
        p, li, blockquote, dd {
            line-height: ${spacing};
            text-align: ${justify ? 'justify' : 'start'};
            hyphens: ${hyphenate ? 'auto' : 'manual'};
        }
    `;

    async function applyTheme() {
        try {
            const response = await fetch('/api/user_settings');
            if (!response.ok) {
                throw new Error(t.failedToFetchSettings);
            }
            const settings = await response.json();
            const theme = settings.theme || 'auto';
            document.documentElement.setAttribute('data-theme', theme);
        } catch (error) {
            console.error('Error applying theme:', error);
            // Fallback to auto theme
            document.documentElement.setAttribute('data-theme', 'auto');
        }
    }

    applyTheme();
    showLoading();


    let view; // To hold the foliate-view instance
    let voices = [];

    // Helper functions from foliate-js/reader.js to format metadata
    const locales = navigator.language || 'en';
    const listFormat = new Intl.ListFormat(locales, { style: 'short', type: 'conjunction' });

    const formatLanguageMap = x => {
        if (!x) return '';
        if (typeof x === 'string') return x;
        const keys = Object.keys(x);
        return x[keys[0]];
    };

    const formatOneContributor = contributor => typeof contributor === 'string'
        ? contributor : formatLanguageMap(contributor?.name);

    const formatContributor = contributor => Array.isArray(contributor)
        ? listFormat.format(contributor.map(formatOneContributor))
        : formatOneContributor(contributor);


    // Expected URL format: /reader/calibre/<book_id> or /reader/anx/<book_id>
    if (pathParts.length === 4 && pathParts[1] === 'reader') {
        const bookType = pathParts[2];
        const bookId = pathParts[3];
        let downloadUrl;

        if (bookType === 'calibre') {
            downloadUrl = `/api/download_book/${bookId}`;
        } else if (bookType === 'anx') {
            downloadUrl = `/api/download_anx_book/${bookId}`;
        }

        if (downloadUrl) {
            loadBook(downloadUrl, bookType, bookId);
        } else {
            showError(t.invalidBookType);
        }
    } else {
        showError(t.invalidUrl);
    }

    async function loadBook(url, bookType, bookId) {
        // The loading spinner is already visible, just proceed with loading
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(t.failedToFetchBook.replace('{statusText}', response.statusText));
            }

            const disposition = response.headers.get('Content-Disposition');
            let filename = 'unknown';
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) {
                    filename = decodeURIComponent(matches[1].replace(/['"]/g, ''));
                }
            }

            const bookBlob = await response.blob();
            const bookFile = new File([bookBlob], filename, { type: bookBlob.type });

            const existingView = readerContainer.querySelector('foliate-view');
            if (existingView) {
                readerContainer.removeChild(existingView);
            }
            view = document.createElement('foliate-view');
            readerContainer.appendChild(view);

            // ANX-CALIBRE-MANAGER DARK MODE PATCH (Event-based)
            await view.open(bookFile);

            if (view.renderer) {
                // ANX-CALIBRE-MANAGER DARK MODE PATCH (Event-based)
                // Must be attached AFTER view.open() but BEFORE the first navigation
                view.renderer.addEventListener('load', (event) => {
                    const iframeDoc = event.detail.doc;
                    if (!iframeDoc) return;

                    const themeSetting = document.documentElement.getAttribute('data-theme') || 'auto';
                    const systemIsDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

                    const effectiveTheme = (themeSetting === 'dark' || (themeSetting === 'auto' && systemIsDark))
                        ? 'dark'
                        : 'light';

                    iframeDoc.documentElement.setAttribute('data-theme', effectiveTheme);

                    const styleId = 'anx-dark-mode-patch';
                    if (iframeDoc.getElementById(styleId)) return;

                    const style = iframeDoc.createElement('style');
                    style.id = styleId;
                    style.textContent = `
                        [data-theme="dark"] * {
                            background-color: #333333 !important;
                            color: #e0e0e0 !important;
                        }
                        [data-theme="dark"] a {
                            color: lightblue !important;
                        }
                        [data-theme="light"] * {
                            background-color: #ffffff !important;
                            color: #000000 !important;
                        }
                        [data-theme="light"] a {
                            color: #0000ee !important;
                        }
                    `;
                    iframeDoc.head.appendChild(style);
                });
                // END PATCH

                view.renderer.setStyles?.(getCSS());
                
                // Load progress before rendering the first page
                if (bookType === 'anx') {
                    try {
                        const progressRes = await fetch(`/api/reader/progress/anx/${bookId}`);
                        if (progressRes.ok) {
                            const progress = await progressRes.json();
                            if (progress.cfi) {
                                await view.goTo(progress.cfi);
                            } else {
                                view.renderer.next();
                            }
                        } else {
                             view.renderer.next();
                        }
                    } catch (e) {
                        console.error("Failed to load progress", e);
                        view.renderer.next();
                    }
                } else {
                    view.renderer.next();
                }

                setupUI(view, bookType, bookId);
                setupTTS(); // Setup TTS after the book is loaded
                hideLoading(); // Hide loading animation after book is loaded
            } else {
                hideLoading(); // Hide loading animation even on error
                showError(t.failedToInitRenderer);
            }
        } catch (error) {
            console.error('Error loading book:', error);
            showError(t.errorLoadingBook.replace('{message}', error.message));
            hideLoading(); // Hide loading on error
        }
    }

    function setupUI(viewInstance, bookType, bookId) {
        const book = viewInstance.book;

        // --- Progress and Reading Time Saving ---
        let accumulatedReadingTime = 0;
        let lastSaveTime = Date.now();
        let currentLocation = null;
        let pageFlipCount = 0;
        const PAGE_FLIP_THRESHOLD = 7; // Save every 7 page flips

        const saveProgress = (isUnloading = false) => {
            if (bookType !== 'anx' || !currentLocation) return;

            const now = Date.now();
            const elapsedSeconds = (now - lastSaveTime) / 1000;
            lastSaveTime = now;

            // Mirror KOReader plugin logic: only log time chunks between 5s and 200min (12000s)
            if (elapsedSeconds > 5 && elapsedSeconds < 12000) {
                accumulatedReadingTime += elapsedSeconds;
            }

            const { cfi, fraction } = currentLocation;
            const readingTimeToSend = Math.round(accumulatedReadingTime);

            if (readingTimeToSend <= 0 && !isUnloading) {
                return;
            }

            const url = `/api/reader/progress/anx/${bookId}`;
            const body = JSON.stringify({
                cfi,
                percentage: fraction,
                reading_time_seconds: readingTimeToSend
            });

            if (isUnloading && navigator.sendBeacon) {
                navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
            } else {
                fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: body,
                    keepalive: true
                }).catch(error => {
                    console.error('Failed to save progress:', error);
                });
            }
            accumulatedReadingTime = 0;
            pageFlipCount = 0; // Reset page flip counter after saving
        };

        viewInstance.addEventListener('relocate', ({ detail }) => {
            currentLocation = detail;
            pageFlipCount++;
            
            // Save progress every 7 page flips
            if (pageFlipCount >= PAGE_FLIP_THRESHOLD) {
                saveProgress();
            }
        });

        window.addEventListener('beforeunload', () => {
            saveProgress(true);
        });


        // 1. Setup Book Info (Title, Author, Cover)
        const title = formatLanguageMap(book.metadata?.title) || t.untitled;
        const author = formatContributor(book.metadata?.author) || t.unknownAuthor;
        document.title = title;
        headerTitle.textContent = title;
        sideBarTitle.textContent = title;
        sideBarAuthor.textContent = author;
        book.getCover?.().then(blob => {
            if (blob) sideBarCover.src = URL.createObjectURL(blob);
        });

        // 2. Setup TOC
        if (book.toc) {
            const tocView = createTOCView(book.toc, href => {
                viewInstance.goTo(href).catch(e => console.error(e));
                closeSideBar();
            });
            tocViewContainer.innerHTML = '';
            tocViewContainer.appendChild(tocView.element);
            viewInstance.addEventListener('relocate', ({ detail }) => {
                if (detail.tocItem?.href) {
                    tocView.setCurrentHref?.(detail.tocItem.href);
                }
            });
        }

        // 3. Setup Navigation (Buttons and Keys)
        leftButton.addEventListener('click', () => viewInstance.goLeft());
        rightButton.addEventListener('click', () => viewInstance.goRight());
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') viewInstance.goLeft();
            if (e.key === 'ArrowRight') viewInstance.goRight();
        });

        // 4. Setup Progress Slider
        progressSlider.addEventListener('input', e => {
            viewInstance.goToFraction(parseFloat(e.target.value));
        });
        viewInstance.addEventListener('relocate', ({ detail }) => {
            progressSlider.value = detail.fraction;
            progressLabel.textContent = `${(detail.fraction * 100).toFixed(1)}%`;
        });

        // 5. Setup Sidebar Toggle
        sidebarButton.addEventListener('click', () => {
            dimmingOverlay.classList.add('show');
            sideBar.classList.add('show');
        });
        dimmingOverlay.addEventListener('click', closeSideBar);

        // 6. Setup TTS Popover
        ttsSettingsButton.addEventListener('click', (e) => {
            e.stopPropagation();
            ttsPopover.classList.toggle('show');
        });

        document.addEventListener('click', (e) => {
            if (!ttsPopover.contains(e.target) && !ttsSettingsButton.contains(e.target)) {
                ttsPopover.classList.remove('show');
            }
        });

        // 7. Setup TTS
        const synth = window.speechSynthesis;
        let utterance = null;
        let ttsStoppedByUser = false; // Flag to control playback flow

        function speakNext(ssmlText) {
            // If the current text block is empty, try the next one.
            if (!ssmlText) {
                const nextSsml = viewInstance.tts.next();
                if (nextSsml) {
                    speakNext(nextSsml);
                } else {
                    // No more text on this page, turn to the next page.
                    viewInstance.renderer.next().then(async () => {
                        if (!ttsStoppedByUser) {
                            await viewInstance.initTTS('sentence');
                            speakNext(viewInstance.tts.start());
                        }
                    });
                }
                return;
            }

            const plainText = ssmlText.replace(/<[^>]+>/g, '');
            if (!plainText.trim()) {
                // If the block is just whitespace, get the next one.
                speakNext(viewInstance.tts.next());
                return;
            }

            utterance = new SpeechSynthesisUtterance(plainText);
            const selectedVoiceURI = localStorage.getItem('tts_voice');
            const selectedVoice = voices.find(v => v.voiceURI === selectedVoiceURI);

            utterance.voice = selectedVoice || voices.find(v => v.lang.startsWith(book.metadata?.language)) || voices.find(v => v.default);
            utterance.rate = parseFloat(localStorage.getItem('tts_rate')) || 1;
            utterance.pitch = parseFloat(localStorage.getItem('tts_pitch')) || 1;
            utterance.lang = book.metadata?.language || 'en-US';

            utterance.onend = () => {
                // When one utterance ends, speak the next block, unless stopped by user.
                if (!ttsStoppedByUser) {
                    speakNext(viewInstance.tts.next());
                }
            };

            utterance.onerror = (event) => {
                console.error('SpeechSynthesisUtterance.onerror', event);
            };

            synth.speak(utterance);
        }

        ttsButton.addEventListener('click', async () => {
            if (synth.speaking || synth.paused) {
                ttsStoppedByUser = true; // Set flag
                synth.cancel();
                viewInstance.tts = null; // Reset tts instance
                return;
            }

            // Cancel any previous utterances before starting a new one
            synth.cancel();

            if (!viewInstance.tts) {
                await viewInstance.initTTS('sentence');
            }
            
            ttsStoppedByUser = false; // Reset flag
            speakNext(viewInstance.tts.start());
        });
    }
    
    function closeSideBar() {
        dimmingOverlay.classList.remove('show');
        sideBar.classList.remove('show');
    }

    function setupTTS() {
        const synth = window.speechSynthesis;
        function populateVoiceList() {
            voices = synth.getVoices();
            console.log('Available voices:', voices);
            const selectedVoiceURI = localStorage.getItem('tts_voice');
            ttsVoice.innerHTML = '';
            if (voices.length === 0) {
                const option = document.createElement('option');
                option.textContent = t.noVoices;
                ttsVoice.appendChild(option);
                return;
            }
            voices.forEach(voice => {
                const option = document.createElement('option');
                option.textContent = `${voice.name} (${voice.lang})`;
                option.setAttribute('data-lang', voice.lang);
                option.setAttribute('data-name', voice.name);
                option.value = voice.voiceURI;
                if (voice.voiceURI === selectedVoiceURI) {
                    option.selected = true;
                }
                ttsVoice.appendChild(option);
            });
        }

        // The voices list is loaded asynchronously.
        // We need to wait for the 'voiceschanged' event.
        populateVoiceList(); // Call it once to try and get the voices
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = populateVoiceList;
        }

        // Load and apply settings from localStorage
        ttsRate.value = localStorage.getItem('tts_rate') || 1;
        ttsRateLabel.textContent = ttsRate.value;
        ttsPitch.value = localStorage.getItem('tts_pitch') || 1;
        ttsPitchLabel.textContent = ttsPitch.value;

        // Event Listeners
        ttsRate.addEventListener('input', () => {
            localStorage.setItem('tts_rate', ttsRate.value);
            ttsRateLabel.textContent = ttsRate.value;
        });
        ttsPitch.addEventListener('input', () => {
            localStorage.setItem('tts_pitch', ttsPitch.value);
            ttsPitchLabel.textContent = ttsPitch.value;
        });
        ttsVoice.addEventListener('change', () => {
            localStorage.setItem('tts_voice', ttsVoice.value);
        });
    }

    function showError(message) {
        readerContainer.innerHTML = `<div style="text-align: center; padding: 50px; color: var(--text-color);"><h2>${message}</h2></div>`;
    }
});