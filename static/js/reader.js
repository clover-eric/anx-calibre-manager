import './foliate/view.js';
import { createTOCView } from './foliate/ui/tree.js';

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
                throw new Error('Failed to fetch user settings');
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
            loadBook(downloadUrl);
        } else {
            showError('Invalid book type specified.');
        }
    } else {
        showError('Invalid URL for book reader.');
    }

    async function loadBook(url) {
        // The loading spinner is already visible, just proceed with loading
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch book: ${response.statusText}`);
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

            await view.open(bookFile);

            if (view.renderer) {
                view.renderer.setStyles?.(getCSS());
                view.renderer.next();
                setupUI(view);
                setupTTS(); // Setup TTS after the book is loaded
                hideLoading(); // Hide loading animation after book is loaded
            } else {
                hideLoading(); // Hide loading animation even on error
                showError('Failed to initialize book renderer.');
            }
        } catch (error) {
            console.error('Error loading book:', error);
            showError(`Error loading book: ${error.message}`);
            hideLoading(); // Hide loading on error
        }
    }

    function setupUI(viewInstance) {
        const book = viewInstance.book;

        // 1. Setup Book Info (Title, Author, Cover)
        const title = formatLanguageMap(book.metadata?.title) || 'Untitled';
        const author = formatContributor(book.metadata?.author) || 'Unknown Author';
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
                option.textContent = 'No voices available';
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