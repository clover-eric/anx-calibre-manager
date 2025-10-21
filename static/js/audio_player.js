import { t, initializeTranslations, sprintf } from './page/translations.js';

document.addEventListener('DOMContentLoaded', () => {
    initializeTranslations();
    // --- State ---
    let currentAudiobooks = [];
    let filteredAudiobooks = [];
    let currentTrackIndex = -1;
    let saveProgressInterval;
    let lastListenLogTime = null;
    let accumulatedListenTime = 0;
    const LISTEN_LOG_THRESHOLD = 30; // Log every 30 seconds
    const AUTO_SAVE_INTERVAL = 420000; // 7 minutes in milliseconds
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    // --- DOM Elements ---
    const dom = {
        body: document.body,
        userId: document.body.dataset.userId,
        isMaintainer: document.body.dataset.isMaintainer === 'true',
        listView: document.querySelector('.list-view'),
        libraryToggleButtons: document.querySelectorAll('.library-toggle button'),
        searchInput: document.getElementById('search-input'),
        audiobookList: document.getElementById('audiobook-list'),
        emptyLibraryMessage: document.getElementById('empty-library-message'),
        loadingOverlay: document.getElementById('library-loading-overlay'),
        audioElement: document.getElementById('audio-element'),
        
        // Desktop Player
        playerView: document.getElementById('player-view'),
        playerPlaceholder: document.getElementById('player-placeholder'),
        playerContent: document.getElementById('player-content'),

        // Mobile Player
        miniPlayer: document.getElementById('mini-player'),
        miniPlayerInfo: document.querySelector('.mini-player-info'),
        miniPlayerCover: document.getElementById('mini-player-cover'),
        miniPlayerTitle: document.getElementById('mini-player-title'),
        miniPlayerArtist: document.getElementById('mini-player-artist'),
        miniPlayerProgressBar: document.getElementById('mini-player-progress-bar'),
        miniPlayerControls: document.querySelector('.mini-player-controls'),
        
        fullPlayerOverlay: document.getElementById('full-player-overlay'),
        fullPlayerCloseBtn: document.getElementById('full-player-close-btn'),
    };

    // --- Utility Functions ---
    const formatTime = (seconds) => {
        if (isNaN(seconds) || seconds < 0) return '0:00';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const applyConditionalMarquee = (container) => {
        setTimeout(() => {
            const marquees = container.querySelectorAll('.marquee');
            marquees.forEach(marquee => {
                const span = marquee.querySelector('span');
                if (span && span.scrollWidth > marquee.clientWidth) {
                    marquee.classList.add('overflowing');
                } else {
                    marquee.classList.remove('overflowing');
                }
            });
        }, 0);
    };
 
     // --- API Functions ---
     const fetchAudiobooks = async (libraryType) => {
        dom.loadingOverlay.style.display = 'flex';
        try {
            const response = await fetch(`/api/audioplayer/list/${libraryType}`);
            if (!response.ok) throw new Error(t.failedToFetchAudiobookList);
            currentAudiobooks = await response.json();
            filterAndRenderList();
        } catch (error) {
            console.error(error);
        } finally {
            dom.loadingOverlay.style.display = 'none';
        }
    };
    
    const fetchProgress = async (taskId) => {
       try {
           const response = await fetch(`/api/audioplayer/progress/${taskId}`);
           if (!response.ok) return { currentTime: 0, totalDuration: 0 };
           return await response.json();
       } catch (error) {
           return { currentTime: 0, totalDuration: 0 };
       }
   };

    const saveProgress = (isUserAction = false) => {
        if (currentTrackIndex === -1 || !dom.audioElement.src || dom.audioElement.currentTime === 0) return;
        const track = currentAudiobooks[currentTrackIndex];
        const currentTime = dom.audioElement.currentTime;
        const playbackRate = dom.audioElement.playbackRate;
        fetch(`/api/audioplayer/progress/${track.task_id}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                currentTime: currentTime,
                totalDuration: dom.audioElement.duration,
                playbackRate: playbackRate,
                isUserAction: isUserAction
            }),
        });
    };

    const logListenTime = (isUserAction = false) => {
        if (currentTrackIndex === -1 || dom.audioElement.paused || !lastListenLogTime) {
            return;
        }

        const now = Date.now();
        const elapsedSeconds = (now - lastListenLogTime) / 1000;
        accumulatedListenTime += elapsedSeconds;
        lastListenLogTime = now;

        if (accumulatedListenTime >= LISTEN_LOG_THRESHOLD) {
            const track = currentAudiobooks[currentTrackIndex];
            if (track.library_type !== 'anx') return; // Only log for anx library books

            const timeToSend = Math.round(accumulatedListenTime);
            accumulatedListenTime = 0;

            fetch('/api/audioplayer/log_listen_time', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    book_id: track.book_id,
                    listen_duration_seconds: timeToSend,
                    isUserAction: isUserAction
                }),
            }).catch(error => console.error('Failed to log listen time:', error));
        }
    };

    // --- Render Functions ---
    const filterAndRenderList = () => {
        const query = dom.searchInput.value.toLowerCase();
        filteredAudiobooks = currentAudiobooks.filter(book => 
            book.title.toLowerCase().includes(query) || 
            book.artist.toLowerCase().includes(query)
        );
        renderAudiobookList();
    };

    const renderAudiobookList = () => {
        dom.audiobookList.innerHTML = '';
        if (filteredAudiobooks.length === 0) {
            dom.audiobookList.style.display = 'none';
            dom.emptyLibraryMessage.style.display = 'flex';
            return;
        }
        
        dom.audiobookList.style.display = 'block';
        dom.emptyLibraryMessage.style.display = 'none';

        filteredAudiobooks.forEach((book) => {
            const originalIndex = currentAudiobooks.findIndex(b => b.task_id === book.task_id);
            const item = document.createElement('div');
            item.className = 'audiobook-item';
            item.dataset.index = originalIndex;

            const titleHtml = `<div class="marquee"><span>${book.title}</span></div>`;
            const artistHtml = `<p class="marquee"><span>${book.artist}</span></p>`;
 
            const canDelete = (book.library_type === 'anx' && book.user_id == dom.userId) ||
                              (book.library_type === 'calibre' && dom.isMaintainer);

            const deleteButtonHtml = canDelete
                ? `<button class="delete-audiobook-btn" title="${t.deleteAudiobook}"><i class="fas fa-trash-alt"></i></button>`
                : '';

             item.innerHTML = `
                 <img src="${book.cover || '/static/images/default-cover.svg'}" alt="${book.title}" class="cover">
                 <div class="info">
                     <div class="info-main">
                         <h4>${titleHtml}</h4>
                         ${artistHtml}
                     </div>
                     <div class="meta">
                         <span>${book.chapter_count} ${t.chapters}</span>
                        <span>${formatTime(book.total_duration)}</span>
                    </div>
                </div>
                ${deleteButtonHtml}
            `;

            item.querySelectorAll('.info, .cover').forEach(el => {
                el.addEventListener('click', () => {
                    document.querySelectorAll('.audiobook-item.active').forEach(el => el.classList.remove('active'));
                    item.classList.add('active');
                    playAudiobook(originalIndex);
                });
            });

            if (canDelete) {
                item.querySelector('.delete-audiobook-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    handleDelete(book.task_id, book.title);
                });
            }
            dom.audiobookList.appendChild(item);
            applyConditionalMarquee(item);
        });
    };

    const handleDelete = async (taskId, title) => {
        const confirmationMessage = sprintf(t.areYouSureYouWantToDelete, { title: title });
        if (!confirm(confirmationMessage)) {
            return;
        }

        try {
            const response = await fetch(`/api/audiobook/delete/${taskId}`, {
                method: 'DELETE',
            });

            const result = await response.json();

            if (response.ok) {
                // Remove from state and re-render
                currentAudiobooks = currentAudiobooks.filter(book => book.task_id !== taskId);
                filterAndRenderList();
                // If the deleted book was playing, stop the player
                if (currentTrackIndex !== -1 && currentAudiobooks[currentTrackIndex]?.task_id === taskId) {
                    dom.audioElement.src = '';
                    // Reset player UI
                }
            } else {
                alert(sprintf(t.errorWithMessage, { message: result.error || t.failedToDeleteAudiobook }));
            }
        } catch (error) {
            console.error('Deletion error:', error);
            alert(t.anUnexpectedErrorOccurred);
        }
    };

    const renderPlayerContent = (track) => {
        const chaptersHtml = track.chapters && track.chapters.length > 0
            ? track.chapters.map((chap, index) => `
                <li data-start="${chap.start}" data-index="${index}">
                    <span class="marquee"><span>${chap.title}</span></span>
                    <span>${formatTime(chap.end - chap.start)}</span>
                </li>`).join('')
            : `<li>${t.noChaptersAvailable}</li>`;

        const metadataHtml = [
            { label: t.album, value: track.album },
            { label: t.albumArtist, value: track.album_artist },
            { label: t.genre, value: track.genre },
            { label: t.year, value: track.year },
            { label: t.composer, value: track.composer },
            { label: t.comment, value: track.comment },
            { label: t.description, value: track.description }
        ]
        .filter(item => item.value)
        .map(item => `<p><strong>${item.label}:</strong> ${item.value}</p>`)
        .join('');
        
        const metadataContainerHtml = metadataHtml
            ? `<div class="track-metadata">${metadataHtml}</div><button class="button metadata-toggle-btn">${t.more}</button>`
            : '';
 
         return `
             <div class="player-top-info">
                 <img src="${track.cover || '/static/images/default-cover.svg'}" alt="Cover" class="player-cover">
                 <div class="track-details">
                     <h2 class="marquee"><span>${track.title}</span></h2>
                     <p class="marquee"><span>${track.artist}</span></p>
                     ${metadataContainerHtml}
                 </div>
             </div>
             <div class="player-chapters-container">
                <ul class="chapter-list">${chaptersHtml}</ul>
            </div>
            <div class="player-bottom-controls">
                <div class="progress-container">
                    <input type="range" class="progress-bar" value="0" step="1">
                    <div class="time-labels">
                        <span class="current-time">00:00</span>
                        <span class="total-duration">00:00</span>
                    </div>
                </div>
                <div class="playback-buttons">
                    <button class="control-button prev-chapter-btn" title="${t.previousChapter}"><i class="fas fa-step-backward"></i></button>
                    <button class="control-button seek-backward-btn" title="${t.seekBackward}"><i class="fas fa-undo"></i></button>
                    <button class="control-button play-pause-btn" title="${t.playPause}"><i class="fas fa-play"></i></button>
                    <button class="control-button seek-forward-btn" title="${t.seekForward}"><i class="fas fa-redo"></i></button>
                    <button class="control-button next-chapter-btn" title="${t.nextChapter}"><i class="fas fa-step-forward"></i></button>
                    <div class="playback-rate-container">
                        <button class="control-button playback-rate-btn" title="${t.playbackSpeed}">1.0x</button>
                        <ul class="playback-rate-list">
                            <!-- Rates will be populated by JS -->
                        </ul>
                    </div>
                </div>
            </div>
        `;
    };

    const bindPlayerEvents = (container) => {
        const playPauseBtn = container.querySelector('.play-pause-btn');
        if (playPauseBtn) playPauseBtn.addEventListener('click', togglePlayPause);

        const prevChapterBtn = container.querySelector('.prev-chapter-btn');
        if (prevChapterBtn) prevChapterBtn.addEventListener('click', () => changeChapter(-1));
 
         const nextChapterBtn = container.querySelector('.next-chapter-btn');
        if (nextChapterBtn) nextChapterBtn.addEventListener('click', () => changeChapter(1));
 
         const seekBackwardBtn = container.querySelector('.seek-backward-btn');
        if (seekBackwardBtn) seekBackwardBtn.addEventListener('click', () => seek(-10));

        const seekForwardBtn = container.querySelector('.seek-forward-btn');
        if (seekForwardBtn) seekForwardBtn.addEventListener('click', () => seek(30));

        const playbackRateContainer = container.querySelector('.playback-rate-container');
        if (playbackRateContainer) {
            const rateBtn = playbackRateContainer.querySelector('.playback-rate-btn');
            const rateList = playbackRateContainer.querySelector('.playback-rate-list');

            // Populate the list
            rateList.innerHTML = playbackRates.map(rate =>
                `<li data-rate="${rate}">${rate.toFixed(1)}x</li>`
            ).join('');

            // Show/hide list
            rateBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                playbackRateContainer.classList.toggle('active');
            });

            // Select rate
            rateList.addEventListener('click', (e) => {
                if (e.target.tagName === 'LI') {
                    const newRate = parseFloat(e.target.dataset.rate);
                    applyPlaybackRate(newRate);
                    playbackRateContainer.classList.remove('active');
                }
            });
        }

        const progressBar = container.querySelector('.progress-bar');
        if (progressBar) {
            let isSeeking = false;
            progressBar.addEventListener('mousedown', () => isSeeking = true);
            progressBar.addEventListener('touchstart', () => isSeeking = true);
            
            progressBar.addEventListener('input', (e) => {
                if (!isSeeking) return;
                // Update time label visually while dragging
                const currentTimeEl = container.querySelector('.current-time');
                if (currentTimeEl) {
                     currentTimeEl.textContent = formatTime(parseFloat(e.target.value));
                }
            });

            progressBar.addEventListener('change', (e) => { // mouseup/touchend
                const track = currentAudiobooks[currentTrackIndex];
                const chapter = track.chapters[getCurrentChapterIndex()];
                if (chapter) {
                    const newTime = chapter.start + parseFloat(e.target.value);
                    dom.audioElement.currentTime = newTime;
                }
                isSeeking = false;
            });
             progressBar.addEventListener('mouseup', () => isSeeking = false);
             progressBar.addEventListener('touchend', () => isSeeking = false);
         }
         container.querySelectorAll('.chapter-list li').forEach(li => {
             li.addEventListener('click', () => {
                 dom.audioElement.currentTime = parseFloat(li.dataset.start);
             });
         });

        const metadataToggleBtn = container.querySelector('.metadata-toggle-btn');
        if (metadataToggleBtn) {
            metadataToggleBtn.addEventListener('click', (e) => {
                const metadataContainer = container.querySelector('.track-metadata');
                metadataContainer.classList.toggle('expanded');
                if (metadataContainer.classList.contains('expanded')) {
                    e.target.textContent = t.less;
                } else {
                    e.target.textContent = t.more;
                }
            });
        }
     };

    // --- Media Session API Integration ---
    const updateMediaSession = (track) => {
        if ('mediaSession' in navigator) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: track.title,
                artist: track.artist,
                album: track.album || 'Audiobook',
                artwork: [
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '96x96', type: 'image/svg+xml' },
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '128x128', type: 'image/svg+xml' },
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '192x192', type: 'image/svg+xml' },
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '256x256', type: 'image/svg+xml' },
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '384x384', type: 'image/svg+xml' },
                    { src: track.cover || '/static/images/default-cover.svg', sizes: '512x512', type: 'image/svg+xml' },
                ]
            });
        }
    };

    const setupMediaSessionHandlers = () => {
        if ('mediaSession' in navigator) {
            navigator.mediaSession.setActionHandler('play', togglePlayPause);
            navigator.mediaSession.setActionHandler('pause', togglePlayPause);
            navigator.mediaSession.setActionHandler('previoustrack', () => changeChapter(-1));
            navigator.mediaSession.setActionHandler('nexttrack', () => changeChapter(1));
            navigator.mediaSession.setActionHandler('seekbackward', () => seek(-10));
            navigator.mediaSession.setActionHandler('seekforward', () => seek(30));
        }
    };

    // --- Player Logic ---
    const playAudiobook = async (index) => {
        saveProgress(true); // Save progress of the current track before switching (user action)
        if (saveProgressInterval) clearInterval(saveProgressInterval);
        currentTrackIndex = index;
        const track = currentAudiobooks[index];
        
        updateMediaSession(track); // Update media session metadata

        // This function now also handles showing the correct view
        const showPlayerDetail = () => {
            if (isMobile) {
                dom.listView.classList.add('playing');
                dom.miniPlayer.classList.remove('hidden');
                dom.miniPlayerCover.src = track.cover || '/static/images/default-cover.svg';
                dom.miniPlayerTitle.innerHTML = `<div class="marquee"><span>${track.title}</span></div>`;
                dom.miniPlayerArtist.innerHTML = `<div class="marquee"><span>${track.artist}</span></div>`;
                applyConditionalMarquee(dom.miniPlayer);

                // --- MODIFICATION START ---
                // Show the full player overlay automatically
                const fullPlayerContent = dom.fullPlayerOverlay.querySelector('.full-player-content');
                fullPlayerContent.innerHTML = renderPlayerContent(track);
                bindPlayerEvents(fullPlayerContent);
                applyConditionalMarquee(fullPlayerContent);
                updateAllPlayerStates(); // Ensure the state is correct on show
                dom.fullPlayerOverlay.classList.remove('hidden');
                // --- MODIFICATION END ---

            } else {
                dom.playerPlaceholder.classList.add('hidden');
                dom.playerContent.innerHTML = renderPlayerContent(track);
                bindPlayerEvents(dom.playerContent);
                applyConditionalMarquee(dom.playerContent);
                dom.playerContent.classList.remove('hidden');
            }
        };

        showPlayerDetail();

        dom.audioElement.src = `/api/audioplayer/stream/${track.task_id}`;
        const progressData = await fetchProgress(track.task_id);
        const savedTime = progressData.currentTime || 0;
        const savedRate = progressData.playbackRate || 1.0;

        applyPlaybackRate(savedRate); // Apply saved rate before playing

        dom.audioElement.addEventListener('loadedmetadata', () => {
            const duration = dom.audioElement.duration;
            if (isFinite(savedTime) && savedTime > 0 && savedTime < duration) {
                dom.audioElement.currentTime = savedTime;
            }
            dom.audioElement.play();
        }, { once: true });

        saveProgressInterval = setInterval(() => {
            saveProgress(false); // Auto-save, not user action
            logListenTime(false); // Auto-log, not user action
        }, AUTO_SAVE_INTERVAL);
    };

    const togglePlayPause = () => {
        if (!dom.audioElement.src) return;
        if (dom.audioElement.paused) {
            dom.audioElement.play();
        } else {
            dom.audioElement.pause();
            saveProgress(true); // Save progress on pause (user action)
            logListenTime(true); // Log listen time on pause (user action)
        }
    };

    const changeTrack = (direction) => {
        if (filteredAudiobooks.length === 0) return;

        // Find the current track's index within the *filtered* list
        const currentFilteredIndex = filteredAudiobooks.findIndex(book =>
            currentAudiobooks.indexOf(book) === currentTrackIndex
        );

        let nextFilteredIndex = currentFilteredIndex + direction;

        if (nextFilteredIndex < 0) {
            nextFilteredIndex = filteredAudiobooks.length - 1;
        }
        if (nextFilteredIndex >= filteredAudiobooks.length) {
            nextFilteredIndex = 0;
        }

        const nextBook = filteredAudiobooks[nextFilteredIndex];
        const nextOriginalIndex = currentAudiobooks.indexOf(nextBook);

        const newActiveItem = dom.audiobookList.querySelector(`[data-index='${nextOriginalIndex}']`);
        if (newActiveItem) {
            document.querySelectorAll('.audiobook-item.active').forEach(el => el.classList.remove('active'));
            newActiveItem.classList.add('active');
            newActiveItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        playAudiobook(nextOriginalIndex);
    };
    
    const seek = (seconds) => { dom.audioElement.currentTime += seconds; };

    const playbackRates = [0.3, 0.5, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0, 2.5, 3.0];

    const applyPlaybackRate = (rate) => {
        dom.audioElement.playbackRate = rate;
        
        document.querySelectorAll('.playback-rate-container').forEach(container => {
            const btn = container.querySelector('.playback-rate-btn');
            const list = container.querySelector('.playback-rate-list');
            if (btn) btn.textContent = `${rate.toFixed(1)}x`;
            if (list) {
                list.querySelectorAll('li').forEach(li => {
                    li.classList.toggle('active', parseFloat(li.dataset.rate) === rate);
                });
            }
        });
        
        // No longer need to save to localStorage, as it's handled by the backend
        // localStorage.setItem('audiobookPlaybackRate', rate);
    };

    const changeChapter = (direction) => {
        const track = currentAudiobooks[currentTrackIndex];
        if (!track || !track.chapters || track.chapters.length === 0) return;
        let newChapterIndex = getCurrentChapterIndex() + direction;
        if (newChapterIndex >= 0 && newChapterIndex < track.chapters.length) {
            dom.audioElement.currentTime = track.chapters[newChapterIndex].start;
        }
    };
 
     const getCurrentChapterIndex = () => {
         const track = currentAudiobooks[currentTrackIndex];
        const currentTime = dom.audioElement.currentTime;
        if (!track || !track.chapters) return -1;
        
        for (let i = track.chapters.length - 1; i >= 0; i--) {
            if (currentTime >= track.chapters[i].start) {
                return i;
            }
        }
        return 0;
    }

    const updateAllPlayerStates = () => {
        const { currentTime, duration, paused } = dom.audioElement;
        
        const playerUIs = [dom.playerContent, dom.fullPlayerOverlay, dom.miniPlayer];
        
        const track = currentAudiobooks[currentTrackIndex];
        const chapterIndex = getCurrentChapterIndex();
        const chapter = track && track.chapters && chapterIndex !== -1 ? track.chapters[chapterIndex] : null;

        playerUIs.forEach(ui => {
            if (!ui || (ui.classList.contains('hidden') && ui.id !== 'mini-player')) return;

            const playPauseIcon = ui.querySelector('.play-pause-btn i');
            if (playPauseIcon) {
                playPauseIcon.classList.toggle('fa-play', paused);
                playPauseIcon.classList.toggle('fa-pause', !paused);
            }

            const progressBar = ui.querySelector('.progress-bar');
            if (progressBar) {
               if (chapter) {
                   const chapterDuration = chapter.end - chapter.start;
                   const timeInChapter = currentTime - chapter.start;
                   progressBar.value = timeInChapter > 0 ? timeInChapter : 0;
                   progressBar.max = chapterDuration > 0 ? chapterDuration : 0;
               } else if (duration > 0) {
                   // Fallback for books without chapters
                   progressBar.value = currentTime;
                   progressBar.max = duration;
               } else {
                   progressBar.value = 0;
                   progressBar.max = 0;
               }
            }
            
            const currentTimeEl = ui.querySelector('.current-time');
            if (currentTimeEl && chapter) {
                currentTimeEl.textContent = formatTime(currentTime - chapter.start);
            } else if (currentTimeEl) {
                currentTimeEl.textContent = formatTime(currentTime);
            }

            const totalDurationEl = ui.querySelector('.total-duration');
            if (totalDurationEl && chapter) {
                totalDurationEl.textContent = formatTime(chapter.end - chapter.start);
            } else if (totalDurationEl) {
                totalDurationEl.textContent = formatTime(duration);
            }
            
            const chapterList = ui.querySelector('.chapter-list');
            if (chapterList) {
                chapterList.querySelectorAll('li').forEach((li, index) => {
                    li.classList.toggle('active', index === chapterIndex);
                });
            }
        });
    };

    // --- Event Listeners ---
    dom.libraryToggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const libraryId = button.dataset.library;
            window.location.href = `/audio_player?library_id=${libraryId}`;
        });
    });

    dom.searchInput.addEventListener('input', filterAndRenderList);

    dom.audioElement.addEventListener('play', () => {
        lastListenLogTime = Date.now();
        updateAllPlayerStates();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
    });
    dom.audioElement.addEventListener('pause', () => {
        updateAllPlayerStates();
        if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
    });
    dom.audioElement.addEventListener('timeupdate', updateAllPlayerStates);
    dom.audioElement.addEventListener('loadedmetadata', updateAllPlayerStates);
    dom.audioElement.addEventListener('ended', () => changeTrack(1));

    // Loading animation handlers
    const toggleLoading = (isLoading) => {
        document.querySelectorAll('.play-pause-btn').forEach(btn => {
            btn.classList.toggle('loading', isLoading);
        });
    };

    dom.audioElement.addEventListener('loadstart', () => toggleLoading(true));
    dom.audioElement.addEventListener('canplay', () => toggleLoading(false));
    dom.audioElement.addEventListener('stalled', () => toggleLoading(false));
    dom.audioElement.addEventListener('error', () => toggleLoading(false));
 
     if (isMobile) {
        // Bind events for the mini player progress bar
        let isMiniSeeking = false;
        dom.miniPlayerProgressBar.addEventListener('mousedown', () => isMiniSeeking = true);
        dom.miniPlayerProgressBar.addEventListener('touchstart', () => isMiniSeeking = true);
        
        dom.miniPlayerProgressBar.addEventListener('input', (e) => {
            if (!isMiniSeeking) return;
            // No time label to update on mini player, so this is just for visual feedback
        });

        dom.miniPlayerProgressBar.addEventListener('change', (e) => {
            if (currentTrackIndex === -1) return;
            const track = currentAudiobooks[currentTrackIndex];
            const chapter = track.chapters[getCurrentChapterIndex()];
            if (chapter) {
                const newTime = chapter.start + parseFloat(e.target.value);
                dom.audioElement.currentTime = newTime;
            }
            isMiniSeeking = false;
        });
        dom.miniPlayerProgressBar.addEventListener('mouseup', () => isMiniSeeking = false);
        dom.miniPlayerProgressBar.addEventListener('touchend', () => isMiniSeeking = false);


         dom.miniPlayerInfo.addEventListener('click', () => {
             const track = currentAudiobooks[currentTrackIndex];
            if (!track) return;
            
            const fullPlayerContent = dom.fullPlayerOverlay.querySelector('.full-player-content');
            fullPlayerContent.innerHTML = renderPlayerContent(track);
            bindPlayerEvents(fullPlayerContent);
            applyConditionalMarquee(fullPlayerContent);
            updateAllPlayerStates();
            dom.fullPlayerOverlay.classList.remove('hidden');
        });

        const changeChapter = (direction) => {
            const track = currentAudiobooks[currentTrackIndex];
            if (!track || !track.chapters) return;
            let newChapterIndex = getCurrentChapterIndex() + direction;
            if (newChapterIndex >= 0 && newChapterIndex < track.chapters.length) {
                dom.audioElement.currentTime = track.chapters[newChapterIndex].start;
            }
        };

        dom.miniPlayerInfo.addEventListener('click', () => {
            const track = currentAudiobooks[currentTrackIndex];
            if (!track) return;
            
            const fullPlayerContent = dom.fullPlayerOverlay.querySelector('.full-player-content');
            fullPlayerContent.innerHTML = renderPlayerContent(track);
            bindPlayerEvents(fullPlayerContent);
            applyConditionalMarquee(fullPlayerContent);
            updateAllPlayerStates();
            dom.fullPlayerOverlay.classList.remove('hidden');
        });

        const miniPlayPauseBtn = dom.miniPlayerControls.querySelector('.play-pause-btn');
        if (miniPlayPauseBtn) miniPlayPauseBtn.addEventListener('click', togglePlayPause);
        
        const miniPrevChapterBtn = dom.miniPlayerControls.querySelector('.prev-chapter-btn');
        if (miniPrevChapterBtn) miniPrevChapterBtn.addEventListener('click', () => changeChapter(-1));

        const miniNextChapterBtn = dom.miniPlayerControls.querySelector('.next-chapter-btn');
        if (miniNextChapterBtn) miniNextChapterBtn.addEventListener('click', () => changeChapter(1));

        dom.fullPlayerCloseBtn.addEventListener('click', () => {
            dom.fullPlayerOverlay.classList.add('hidden');
        });
    }

    window.addEventListener('beforeunload', () => {
        saveProgress(true); // Save on page close (user action)
        logListenTime(true); // Log on page close (user action)
    });

    // Keyboard shortcuts listener (keep for non-media keys)
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === ' ') {
            e.preventDefault();
            togglePlayPause();
        }
    });

    // --- Initial Load ---
    setupMediaSessionHandlers(); // Set up media key handlers
    const initialLibraryId = dom.body.dataset.libraryId || 'calibre';
    const urlParams = new URLSearchParams(window.location.search);
    const taskIdToPlay = urlParams.get('task_id');

    // Restore playback rate - This is now handled within playAudiobook after fetching progress
    // const savedRate = parseFloat(localStorage.getItem('audiobookPlaybackRate')) || 1.0;
    // applyPlaybackRate(savedRate);

    // Global listener to close rate list
    document.addEventListener('click', () => {
        document.querySelectorAll('.playback-rate-container.active').forEach(container => {
            container.classList.remove('active');
        });
    });

    fetchAudiobooks(initialLibraryId).then(() => {
        if (taskIdToPlay) {
            const indexToPlay = currentAudiobooks.findIndex(book => book.task_id === taskIdToPlay);
            if (indexToPlay !== -1) {
                // Highlight the item in the list
                const itemInList = dom.audiobookList.querySelector(`[data-index='${indexToPlay}']`);
                if (itemInList) {
                    itemInList.classList.add('active');
                    itemInList.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                playAudiobook(indexToPlay);
            } else {
                console.warn(`Task ID ${taskIdToPlay} not found in the current library view.`);
            }
        }
    });
});
