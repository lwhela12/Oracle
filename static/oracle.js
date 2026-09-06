        const portal = document.getElementById('consultation-portal');
        const readingStage = document.getElementById('reading-stage');
        const spreadStep = document.getElementById('spread-step');
        const spreadStepTitle = document.getElementById('spread-step-title');
        const spreadOptions = document.getElementById('spread-options');
        const userInquiry = document.getElementById('user-inquiry');
        const consultBtn = document.getElementById('consult-btn');
        const visualStageCard = document.getElementById('visual-stage-card');
        const activeReadingBadge = document.getElementById('active-reading-badge');
        const seekerInquiryDisplay = document.getElementById('seeker-inquiry-display');
        const oracleStreamText = document.getElementById('oracle-stream-text');
        const thinkingIndicator = document.getElementById('thinking-indicator');
        const themeBtn = document.getElementById('theme-btn');
        const soundBtn = document.getElementById('sound-btn');
        const musicBtn = document.getElementById('music-btn');
        const historyDrawer = document.getElementById('history-drawer');
        const historyList = document.getElementById('history-list');

        // State
        let currentTradition = 'tarot';
        let currentSpreadType = '3-card';
        let currentReadingData = null;
        let soundEnabled = localStorage.getItem('soundEnabled') === 'true';
        let musicEnabled = localStorage.getItem('musicEnabled') === 'true';
        let audioContext = null;
        let ambientOscillator = null;

        // Session ID Persistence
        let sessionId = sessionStorage.getItem('oracle_session_id');
        if (!sessionId) {
            sessionId = 'session_' + (window.crypto && crypto.randomUUID ? crypto.randomUUID() : (Date.now() + '_' + Math.random().toString(36).substring(2)));
            sessionStorage.setItem('oracle_session_id', sessionId);
        }

        // Available Spreads Configuration
        const TRADITION_SPREADS = {
            tarot: {
                title: 'Choose your spread',
                badgeTitle: 'Tarot reading',
                options: [
                    { id: '3-card', label: 'Three cards' },
                    { id: 'yes-no', label: 'Single card' },
                    { id: '5-card', label: 'Five-card cross' },
                    { id: 'celtic', label: 'Celtic Cross' }
                ],
                default: '3-card',
                placeholder: 'What question or life situation do you bring to the tarot? (or leave blank for general guidance)'
            },
            runes: {
                title: 'Choose your spread',
                badgeTitle: 'Rune reading',
                options: [
                    { id: 'norns', label: 'Three Norns' },
                    { id: 'single', label: 'Single rune' },
                    { id: 'five-cross', label: 'Five-rune cross' },
                    { id: 'thor-hammer', label: 'Thor’s Hammer' },
                    { id: 'nine-worlds', label: 'Nine Worlds' }
                ],
                default: 'norns',
                placeholder: 'What question or life situation do you bring to the Elder Futhark runes? (or leave blank for general guidance)'
            },
            iching: {
                title: 'I Ching Hexagram Casting',
                badgeTitle: 'I Ching reading',
                options: [
                    { id: 'iching', label: 'Hexagram casting' }
                ],
                default: 'iching',
                placeholder: 'What question or decision do you bring to the Book of Changes?'
            },
            number: {
                title: 'Cosmic Numerology Omen',
                badgeTitle: 'Numerology reading',
                options: [
                    { id: 'number', label: 'Number reading' }
                ],
                default: 'number',
                placeholder: 'What life path or inquiry do you bring to the cosmos?'
            }
        };

        // Helper to return clean vector SVG emblem for each tradition
        function getTraditionEmblemSvg(key) {
            if (key === 'tarot') {
                return `
                    <svg viewBox="0 0 48 48" width="34" height="34" fill="none" class="tradition-emblem-svg">
                        <circle cx="24" cy="24" r="22" stroke="url(#goldGrad)" stroke-width="1.5" stroke-dasharray="2 2" opacity="0.6"/>
                        <circle cx="24" cy="24" r="18" stroke="url(#goldGrad)" stroke-width="1.2"/>
                        <path d="M24 8v5 M24 35v5 M8 24h5 M35 24h5 M12.7 12.7l3.5 3.5 M31.8 31.8l3.5 3.5 M12.7 35.3l3.5-3.5 M31.8 16.2l3.5-3.5" stroke="url(#goldGrad)" stroke-width="1.2" stroke-linecap="round"/>
                        <path d="M19 24a5 5 0 1 1 10 0 5 5 0 0 1-10 0z" fill="rgba(212, 175, 55, 0.2)" stroke="url(#goldGrad)" stroke-width="1.4"/>
                        <circle cx="24" cy="24" r="2.2" fill="url(#goldGrad)"/>
                        <path d="M17 24c2.5-4 11.5-4 14 0c-2.5 4-11.5 4-14 0z" stroke="url(#goldGrad)" stroke-width="1" fill="none"/>
                    </svg>
                `;
            } else if (key === 'runes') {
                return `
                    <svg viewBox="0 0 48 48" width="34" height="34" fill="none" class="tradition-emblem-svg">
                        <polygon points="24,3 42,13.5 42,34.5 24,45 6,34.5 6,13.5" stroke="url(#goldGrad)" stroke-width="1.4" fill="rgba(212, 175, 55, 0.08)"/>
                        <circle cx="24" cy="24" r="16" stroke="url(#goldGrad)" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>
                        <path d="M24 10v28" stroke="url(#goldGrad)" stroke-width="2.2" stroke-linecap="round"/>
                        <path d="M16 16l8 7l8-7" stroke="url(#goldGrad)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        <path d="M24 23l7-5 M24 28l7-5" stroke="url(#goldGrad)" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                `;
            } else if (key === 'iching') {
                return `
                    <svg viewBox="0 0 48 48" width="34" height="34" fill="none" class="tradition-emblem-svg">
                        <circle cx="24" cy="24" r="22" stroke="url(#goldGrad)" stroke-width="1.2"/>
                        <g stroke="url(#goldGrad)" stroke-width="1.4" stroke-linecap="round" opacity="0.85">
                            <line x1="20" y1="5" x2="28" y2="5"/><line x1="20" y1="7.5" x2="28" y2="7.5"/><line x1="20" y1="10" x2="28" y2="10"/>
                            <line x1="20" y1="38" x2="23" y2="38"/><line x1="25" y1="38" x2="28" y2="38"/>
                            <line x1="20" y1="40.5" x2="23" y2="40.5"/><line x1="25" y1="40.5" x2="28" y2="40.5"/>
                            <line x1="20" y1="43" x2="23" y2="43"/><line x1="25" y1="43" x2="28" y2="43"/>
                        </g>
                        <circle cx="24" cy="24" r="12" stroke="url(#goldGrad)" stroke-width="1.4" fill="#0f0c1b"/>
                        <path d="M24 12 A6 6 0 0 1 24 24 A6 6 0 0 0 24 36 A12 12 0 0 1 24 12 Z" fill="url(#goldGrad)"/>
                        <circle cx="24" cy="18" r="1.8" fill="#0f0c1b"/>
                        <circle cx="24" cy="30" r="1.8" fill="url(#goldGrad)"/>
                    </svg>
                `;
            } else {
                return `
                    <svg viewBox="0 0 48 48" width="34" height="34" fill="none" class="tradition-emblem-svg">
                        <circle cx="24" cy="24" r="22" stroke="url(#goldGrad)" stroke-width="1.2" stroke-dasharray="1 3"/>
                        <ellipse cx="24" cy="24" rx="19" ry="8" stroke="url(#goldGrad)" stroke-width="1.3" transform="rotate(30 24 24)"/>
                        <ellipse cx="24" cy="24" rx="19" ry="8" stroke="url(#goldGrad)" stroke-width="1.3" transform="rotate(-30 24 24)"/>
                        <ellipse cx="24" cy="24" rx="19" ry="8" stroke="url(#goldGrad)" stroke-width="1.3" transform="rotate(90 24 24)"/>
                        <circle cx="24" cy="24" r="3.5" fill="url(#goldGrad)"/>
                        <circle cx="24" cy="24" r="7" stroke="url(#goldGrad)" stroke-width="1" stroke-dasharray="2 2" opacity="0.6"/>
                    </svg>
                `;
            }
        }

        let runeAllowReversals = true;
        let runeIncludeWyrd = false;

        // Web Audio Synthesizer
        function initAudio() {
            if (!audioContext) {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (AudioCtx) audioContext = new AudioCtx();
            }
            if (audioContext && audioContext.state === 'suspended') {
                audioContext.resume();
            }
        }

        const sounds = {
            cardFlip: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                const osc = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc.connect(gain);
                gain.connect(audioContext.destination);
                osc.frequency.value = 420;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.12, audioContext.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.18);
                osc.start();
                osc.stop(audioContext.currentTime + 0.18);
            },
            cardShuffle: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                for (let i = 0; i < 3; i++) {
                    setTimeout(() => {
                        const osc = audioContext.createOscillator();
                        const gain = audioContext.createGain();
                        osc.connect(gain);
                        gain.connect(audioContext.destination);
                        osc.frequency.value = 220 + Math.random() * 80;
                        osc.type = 'triangle';
                        gain.gain.setValueAtTime(0.06, audioContext.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.09);
                        osc.start();
                        osc.stop(audioContext.currentTime + 0.09);
                    }, i * 45);
                }
            },
            stoneClack: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                const osc1 = audioContext.createOscillator();
                const osc2 = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc1.connect(gain);
                osc2.connect(gain);
                gain.connect(audioContext.destination);
                osc1.frequency.setValueAtTime(160 + Math.random() * 40, audioContext.currentTime);
                osc1.frequency.exponentialRampToValueAtTime(70, audioContext.currentTime + 0.12);
                osc1.type = 'triangle';
                osc2.frequency.setValueAtTime(340 + Math.random() * 50, audioContext.currentTime);
                osc2.frequency.exponentialRampToValueAtTime(120, audioContext.currentTime + 0.08);
                osc2.type = 'sine';
                gain.gain.setValueAtTime(0.18, audioContext.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.13);
                osc1.start();
                osc2.start();
                osc1.stop(audioContext.currentTime + 0.13);
                osc2.stop(audioContext.currentTime + 0.13);
            },
            messageSend: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                const osc = audioContext.createOscillator();
                const gain = audioContext.createGain();
                osc.connect(gain);
                gain.connect(audioContext.destination);
                osc.frequency.value = 580;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.08, audioContext.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.14);
                osc.start();
                osc.stop(audioContext.currentTime + 0.14);
            },
            chime: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                [523.25, 659.25, 783.99].forEach((freq, i) => {
                    setTimeout(() => {
                        const osc = audioContext.createOscillator();
                        const gain = audioContext.createGain();
                        osc.connect(gain);
                        gain.connect(audioContext.destination);
                        osc.frequency.value = freq;
                        osc.type = 'sine';
                        gain.gain.setValueAtTime(0.1, audioContext.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.7);
                        osc.start();
                        osc.stop(audioContext.currentTime + 0.7);
                    }, i * 90);
                });
            },
            coinClatter: () => {
                if (!soundEnabled) return;
                initAudio();
                if (!audioContext) return;
                // Realistic metallic bronze coins clattering on a lacquer board
                const numStrikes = 6;
                for (let i = 0; i < numStrikes; i++) {
                    setTimeout(() => {
                        const osc = audioContext.createOscillator();
                        const gain = audioContext.createGain();
                        osc.connect(gain);
                        gain.connect(audioContext.destination);
                        // High metallic bronze resonance clinks
                        const baseFreqs = [1850, 2150, 2480, 2920, 3250];
                        osc.frequency.value = baseFreqs[i % baseFreqs.length] + (Math.random() * 140 - 70);
                        osc.type = 'sine';
                        const strikeVolume = 0.09 * Math.pow(0.72, i);
                        gain.gain.setValueAtTime(strikeVolume, audioContext.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.0005, audioContext.currentTime + 0.06 + Math.random() * 0.04);
                        osc.start();
                        osc.stop(audioContext.currentTime + 0.11);
                    }, i * (50 + Math.random() * 25));
                }
            }
        };

        // Ambient Drone Music
        function startAmbientMusic() {
            if (!musicEnabled || ambientOscillator) return;
            initAudio();
            if (!audioContext) return;
            ambientOscillator = {
                osc1: audioContext.createOscillator(),
                osc2: audioContext.createOscillator(),
                gain: audioContext.createGain()
            };
            ambientOscillator.osc1.frequency.value = 110;
            ambientOscillator.osc2.frequency.value = 165;
            ambientOscillator.gain.gain.value = 0.025;
            ambientOscillator.osc1.connect(ambientOscillator.gain);
            ambientOscillator.osc2.connect(ambientOscillator.gain);
            ambientOscillator.gain.connect(audioContext.destination);
            ambientOscillator.osc1.start();
            ambientOscillator.osc2.start();
        }

        function stopAmbientMusic() {
            if (ambientOscillator) {
                try {
                    ambientOscillator.osc1.stop();
                    ambientOscillator.osc2.stop();
                } catch(e) {}
                ambientOscillator = null;
            }
        }

        // Card Visual Icons
        function getCardIcon(card) {
            return getTraditionEmblemSvg('tarot');
        }

        function renderMarkdown(raw) {
            let parsed = marked.parse(raw);
            if (parsed.includes('<table>') && parsed.includes('</table>')) {
                parsed = parsed.replace(/<table>/g, '<div class="table-responsive"><table>')
                               .replace(/<\/table>/g, '</table></div>');
            }
            return window.DOMPurify ? DOMPurify.sanitize(parsed) : parsed;
        }

        function getCardSlug(card) {
            return card.name.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/(^-|-$)/g, '');
        }

        // Card Zoom Lightbox Controller
        let activeTarotSpread = null;
        let activeZoomIndex = 0;

        function openCardZoom(index) {
            if (!activeTarotSpread || !activeTarotSpread.cards || !activeTarotSpread.cards[index]) return;
            activeZoomIndex = index;
            updateZoomDialogContent();
            const dialog = document.getElementById('cardZoomDialog');
            if (dialog) {
                if (!dialog.open) {
                    dialog.showModal();
                    sounds.cardFlip();
                }
            }
        }

        function updateZoomDialogContent() {
            if (!activeTarotSpread || !activeTarotSpread.cards) return;
            const card = activeTarotSpread.cards[activeZoomIndex];
            const position = (activeTarotSpread.positions && activeTarotSpread.positions[activeZoomIndex]) || `Card ${activeZoomIndex + 1}`;
            const total = activeTarotSpread.cards.length;
            const slug = getCardSlug(card);

            const zoomCardEl = document.getElementById('zoomCardEl');
            const zoomImg = document.getElementById('zoomCardImg');
            const zoomFallback = document.getElementById('zoomCardFallback');
            const zoomBadge = document.getElementById('zoomPositionBadge');
            const zoomTitle = document.getElementById('zoomCardName');
            const zoomCounter = document.getElementById('zoomCardCounter');
            const prevBtn = document.getElementById('cardZoomPrev');
            const nextBtn = document.getElementById('cardZoomNext');

            if (zoomBadge) zoomBadge.textContent = position;
            if (zoomTitle) zoomTitle.textContent = card.name;
            if (zoomCounter) zoomCounter.textContent = `Card ${activeZoomIndex + 1} of ${total}`;

            if (prevBtn) prevBtn.style.display = total > 1 ? 'flex' : 'none';
            if (nextBtn) nextBtn.style.display = total > 1 ? 'flex' : 'none';

            // Always open face-up to display the artwork
            if (zoomCardEl) zoomCardEl.classList.add('flipped');

            if (zoomImg) {
                zoomImg.style.display = 'block';
                zoomImg.src = `/static/cards/tarot/${slug}.webp`;
                zoomImg.alt = card.name;
                zoomImg.onerror = () => {
                    zoomImg.style.display = 'none';
                    if (zoomFallback) {
                        zoomFallback.style.display = 'flex';
                        const posEl = document.getElementById('zoomCardPosFallback');
                        const iconEl = document.getElementById('zoomCardIconFallback');
                        const nameEl = document.getElementById('zoomCardNameFallback');
                        const suitEl = document.getElementById('zoomCardSuitFallback');
                        if (posEl) posEl.textContent = position;
                        if (iconEl) iconEl.textContent = getCardIcon(card);
                        if (nameEl) nameEl.textContent = card.name;
                        if (suitEl) suitEl.textContent = card.suit || '';
                    }
                };
            }
            if (zoomFallback) zoomFallback.style.display = 'none';
        }

        // Initialize Card Zoom Lightbox Listeners
        const cardZoomDialog = document.getElementById('cardZoomDialog');
        const cardZoomClose = document.getElementById('cardZoomClose');
        const cardZoomPrev = document.getElementById('cardZoomPrev');
        const cardZoomNext = document.getElementById('cardZoomNext');
        const zoomCardEl = document.getElementById('zoomCardEl');
        const zoomFlipBtn = document.getElementById('zoomFlipBtn');

        if (cardZoomDialog) {
            // Light-dismiss when clicking outside the dialog content box
            cardZoomDialog.addEventListener('click', (event) => {
                const container = cardZoomDialog.querySelector('.card-zoom-container');
                if (container && !container.contains(event.target)) {
                    cardZoomDialog.close();
                }
            });

            if (cardZoomClose) {
                cardZoomClose.addEventListener('click', () => cardZoomDialog.close());
            }

            if (zoomCardEl) {
                zoomCardEl.addEventListener('click', () => {
                    zoomCardEl.classList.toggle('flipped');
                    sounds.cardFlip();
                });
            }

            if (zoomFlipBtn) {
                zoomFlipBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (zoomCardEl) {
                        zoomCardEl.classList.toggle('flipped');
                        sounds.cardFlip();
                    }
                });
            }

            if (cardZoomPrev) {
                cardZoomPrev.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (activeTarotSpread && activeTarotSpread.cards && activeTarotSpread.cards.length > 1) {
                        activeZoomIndex = (activeZoomIndex - 1 + activeTarotSpread.cards.length) % activeTarotSpread.cards.length;
                        updateZoomDialogContent();
                        sounds.cardFlip();
                    }
                });
            }

            if (cardZoomNext) {
                cardZoomNext.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (activeTarotSpread && activeTarotSpread.cards && activeTarotSpread.cards.length > 1) {
                        activeZoomIndex = (activeZoomIndex + 1) % activeTarotSpread.cards.length;
                        updateZoomDialogContent();
                        sounds.cardFlip();
                    }
                });
            }

            window.addEventListener('keydown', (e) => {
                if (!cardZoomDialog.open) return;
                if (e.key === 'ArrowLeft') {
                    if (cardZoomPrev) cardZoomPrev.click();
                } else if (e.key === 'ArrowRight') {
                    if (cardZoomNext) cardZoomNext.click();
                } else if (e.key === ' ' || e.key === 'f' || e.key === 'F') {
                    e.preventDefault();
                    if (zoomCardEl) {
                        zoomCardEl.classList.toggle('flipped');
                        sounds.cardFlip();
                    }
                }
            });
        }

        // Rune Zoom Lightbox Controller
        let activeRuneSpread = null;
        let activeRuneZoomIndex = 0;

        const RUNE_AETTS = {
            fehu: "Freyr's Aett • Creation & Wealth",
            uruz: "Freyr's Aett • Primordial Vitality & Strength",
            thurisaz: "Freyr's Aett • Reactive Power & Breakthrough",
            ansuz: "Freyr's Aett • Odin's Wisdom & Divine Breath",
            raidho: "Freyr's Aett • Cosmic Journey & Order",
            kenaz: "Freyr's Aett • Torch, Craft & Inner Fire",
            gebo: "Freyr's Aett • Sacred Gift & Equal Exchange",
            wunjo: "Freyr's Aett • Joy, Harmony & Fellowship",
            hagalaz: "Hagal's Aett • Cosmic Egg & Transformation",
            nauthiz: "Hagal's Aett • Need, Friction & Endurance",
            isa: "Hagal's Aett • Glacier, Stillness & Focus",
            jera: "Hagal's Aett • Harvest & Natural Cycles",
            eihwaz: "Hagal's Aett • Yew Tree & Cosmic Axis",
            perthro: "Hagal's Aett • Mystery, Chance & Fate",
            algiz: "Hagal's Aett • Elk & Divine Sanctuary",
            sowilo: "Hagal's Aett • Solar Victory & Wholeness",
            tiwaz: "Tyr's Aett • Honor, Law & North Star",
            berkano: "Tyr's Aett • Birch, Earth Mother & Renewal",
            ehwaz: "Tyr's Aett • Horse, Trust & Dynamic Movement",
            mannaz: "Tyr's Aett • Humanity & Collective Self",
            laguz: "Tyr's Aett • Deep Ocean & Subconscious Tides",
            ingwaz: "Tyr's Aett • Seed of Potential & Internal Growth",
            dagaz: "Tyr's Aett • Dawn, Awakening & Illumination",
            othala: "Tyr's Aett • Ancestral Heritage & Sacred Land",
            wyrd: "The Void • Cosmic Loom of the Norns & Destiny"
        };

        function openRuneZoom(index) {
            if (!activeRuneSpread || !activeRuneSpread.runes || !activeRuneSpread.runes[index]) return;
            activeRuneZoomIndex = index;
            updateRuneZoomContent();
            const dialog = document.getElementById('runeZoomDialog');
            if (dialog) {
                if (!dialog.open) {
                    dialog.showModal();
                    sounds.stoneClack();
                }
            }
        }

        function updateRuneZoomContent() {
            if (!activeRuneSpread || !activeRuneSpread.runes) return;
            const rune = activeRuneSpread.runes[activeRuneZoomIndex];
            const position = (activeRuneSpread.positions && activeRuneSpread.positions[activeRuneZoomIndex]) || `Rune ${activeRuneZoomIndex + 1}`;
            const total = activeRuneSpread.runes.length;
            const runeKey = (rune.key || rune.name.toLowerCase()).replace(/[^a-z0-9]+/g, '');
            const isRev = Boolean(rune.is_reversed);

            const zoomImg = document.getElementById('zoomRuneImg');
            const zoomFallback = document.getElementById('zoomRuneFallback');
            const zoomBadge = document.getElementById('zoomRunePosition');
            const zoomTitle = document.getElementById('zoomRuneName');
            const zoomAett = document.getElementById('zoomRuneAett');
            const zoomMeaning = document.getElementById('zoomRuneMeaning');
            const zoomCounter = document.getElementById('zoomRuneCounter');
            const prevBtn = document.getElementById('runeZoomPrev');
            const nextBtn = document.getElementById('runeZoomNext');

            if (zoomBadge) {
                zoomBadge.innerHTML = isRev 
                    ? `${position} &bull; <span style="color: #fca5a5;">ᛦ MERKSTAVE (REVERSED)</span>`
                    : `${position} &bull; <span style="color: var(--accent-gold);">ᛚ UPRIGHT</span>`;
            }
            if (zoomTitle) {
                zoomTitle.textContent = `${rune.symbol} ${rune.name}${isRev ? ' (Merkstave)' : ''}`;
            }
            if (zoomAett) zoomAett.textContent = RUNE_AETTS[runeKey] || "Elder Futhark Rune";
            
            if (zoomMeaning) {
                if (isRev) {
                    zoomMeaning.innerHTML = `
                        <div style="color: #fca5a5; font-weight: 700; margin-bottom: 4px; font-family: 'Cinzel', serif;">Reversed meaning</div>
                        <div style="margin-bottom: 6px; font-size: 16px;">${rune.active_meaning || rune.merkstave || rune.meaning}</div>
                        <div style="font-size: 13px; color: var(--text-muted);"><em>Keywords:</em> ${rune.active_keywords || rune.merkstave_keywords || rune.keywords}</div>
                        <div style="margin-top: 10px; font-size: 13px; opacity: 0.8; border-top: 1px dashed rgba(229,193,88,0.25); padding-top: 8px;">
                            <strong>Upright Essence:</strong> ${rune.meaning}
                        </div>
                    `;
                } else {
                    zoomMeaning.innerHTML = `
                        <div style="color: var(--accent-gold); font-weight: 700; margin-bottom: 4px; font-family: 'Cinzel', serif;">Upright meaning</div>
                        <div style="margin-bottom: 6px; font-size: 16px;">${rune.meaning}</div>
                        <div style="font-size: 13px; color: var(--text-muted);"><em>Keywords:</em> ${rune.keywords || ''}</div>
                    `;
                }
            }
            if (zoomCounter) zoomCounter.textContent = `Rune ${activeRuneZoomIndex + 1} of ${total}`;

            if (prevBtn) prevBtn.style.display = total > 1 ? 'flex' : 'none';
            if (nextBtn) nextBtn.style.display = total > 1 ? 'flex' : 'none';

            if (zoomImg) {
                zoomImg.style.display = 'block';
                zoomImg.src = `/static/runes/${runeKey}.webp`;
                zoomImg.alt = rune.name;
                zoomImg.style.transform = isRev ? 'rotate(180deg)' : 'none';
                zoomImg.onerror = () => {
                    zoomImg.style.display = 'none';
                    if (zoomFallback) {
                        zoomFallback.style.display = 'flex';
                        zoomFallback.style.transform = isRev ? 'rotate(180deg)' : 'none';
                        const sym = document.getElementById('zoomRuneSymbolFallback');
                        if (sym) {
                            sym.textContent = rune.symbol;
                            sym.className = 'pebble-glyph';
                            if (['hagalaz', 'nauthiz', 'isa', 'jera', 'eihwaz', 'perthro', 'algiz', 'sowilo'].includes(runeKey)) {
                                sym.classList.add('frost');
                            } else if (['tiwaz', 'berkano', 'ehwaz', 'mannaz', 'laguz', 'ingwaz', 'dagaz', 'othala'].includes(runeKey)) {
                                sym.classList.add('amethyst');
                            }
                        }
                    }
                };
            }
            if (zoomFallback) {
                zoomFallback.style.display = 'none';
                zoomFallback.style.transform = isRev ? 'rotate(180deg)' : 'none';
            }
        }

        // Initialize Rune Zoom Lightbox Listeners
        const runeZoomDialog = document.getElementById('runeZoomDialog');
        const runeZoomClose = document.getElementById('runeZoomClose');
        const runeZoomPrev = document.getElementById('runeZoomPrev');
        const runeZoomNext = document.getElementById('runeZoomNext');

        if (runeZoomDialog) {
            runeZoomDialog.addEventListener('click', (event) => {
                const container = runeZoomDialog.querySelector('.card-zoom-container');
                if (container && !container.contains(event.target)) {
                    runeZoomDialog.close();
                }
            });

            if (runeZoomClose) {
                runeZoomClose.addEventListener('click', () => runeZoomDialog.close());
            }

            if (runeZoomPrev) {
                runeZoomPrev.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (activeRuneSpread && activeRuneSpread.runes && activeRuneSpread.runes.length > 1) {
                        activeRuneZoomIndex = (activeRuneZoomIndex - 1 + activeRuneSpread.runes.length) % activeRuneSpread.runes.length;
                        updateRuneZoomContent();
                        sounds.stoneClack();
                    }
                });
            }

            if (runeZoomNext) {
                runeZoomNext.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (activeRuneSpread && activeRuneSpread.runes && activeRuneSpread.runes.length > 1) {
                        activeRuneZoomIndex = (activeRuneZoomIndex + 1) % activeRuneSpread.runes.length;
                        updateRuneZoomContent();
                        sounds.stoneClack();
                    }
                });
            }

            window.addEventListener('keydown', (e) => {
                if (!runeZoomDialog.open) return;
                if (e.key === 'ArrowLeft') {
                    if (runeZoomPrev) runeZoomPrev.click();
                } else if (e.key === 'ArrowRight') {
                    if (runeZoomNext) runeZoomNext.click();
                }
            });

            // 3D physical object inspection parallax in lightbox
            const zoomContainer = runeZoomDialog.querySelector('.card-zoom-container');
            const zoomImg = document.getElementById('zoomRuneImg');
            const zoomPebble = document.getElementById('zoomRuneFallback');
            if (zoomContainer) {
                zoomContainer.addEventListener('mousemove', (e) => {
                    const rect = zoomContainer.getBoundingClientRect();
                    const x = (e.clientX - rect.left) / rect.width - 0.5;
                    const y = (e.clientY - rect.top) / rect.height - 0.5;
                    const rotX = (-y * 22).toFixed(2);
                    const rotY = (x * 22).toFixed(2);
                    const target = (zoomImg && zoomImg.style.display !== 'none') ? zoomImg : zoomPebble;
                    if (target) {
                        target.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.04) translateZ(20px)`;
                    }
                });
                zoomContainer.addEventListener('mouseleave', () => {
                    const target = (zoomImg && zoomImg.style.display !== 'none') ? zoomImg : zoomPebble;
                    if (target) {
                        target.style.transition = 'transform 0.4s ease';
                        target.style.transform = '';
                        setTimeout(() => { target.style.transition = ''; }, 400);
                    }
                });
            }
        }

        // Renders properly centered visual cards (no bottom cutoff!)
        function renderVisualStage(metadata) {
            visualStageCard.innerHTML = '';
            const themeTradition = metadata.type || currentTradition || 'tarot';
            visualStageCard.className = `visual-stage-card stage-theme-${themeTradition}`;

            if (metadata.type === 'tarot' && metadata.cards) {
                activeTarotSpread = metadata;
                sounds.cardShuffle();

                // Helper to create card element with image loading & graceful fallback
                const makeCardEl = (card, position, index, extraClass = '') => {
                    const wrap = document.createElement('div');
                    wrap.className = 'tarot-card-wrapper' + (extraClass ? ' ' + extraClass : '');
                    wrap.setAttribute('title', `Click to zoom into ${card.name} (${position})`);
                    wrap.setAttribute('data-pos-idx', index);
                    wrap.setAttribute('role', 'button');
                    wrap.tabIndex = 0;
                    wrap.setAttribute('aria-label', `${position}: ${card.name}. View card`);
                    wrap.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCardZoom(index); } });
                    const slug = getCardSlug(card);

                    wrap.innerHTML = `
                        <div class="tarot-card">
                            <div class="card-face card-back"></div>
                            <div class="card-face card-front">
                                <img src="/static/cards/tarot/${slug}.webp" 
                                     alt="${card.name}" 
                                     class="card-img"
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'; const b = this.parentElement.querySelector('.card-overlay-badge'); if(b) b.style.display='none';">
                                <div class="card-art-fallback" style="display: none;">
                                    <div class="card-position">${position}</div>
                                    <div class="card-icon">${getCardIcon(card)}</div>
                                    <div class="card-name">${card.name}</div>
                                    ${card.suit ? `<div class="card-suit">${card.suit}</div>` : ''}
                                </div>
                                <div class="card-overlay-badge top-badge"><span class="card-position-label">${position}</span><span class="card-position-number">${index + 1}</span></div>
                            </div>
                        </div>
                    `;
                    const cardEl = wrap.querySelector('.tarot-card');
                    setTimeout(() => {
                        cardEl.classList.add('flipped');
                        sounds.cardFlip();
                    }, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 80 + index * 60);

                    // Clicking the dealt card opens high-resolution zoom view
                    wrap.addEventListener('click', () => {
                        openCardZoom(index);
                    });
                    return wrap;
                };

                // Dedicated authentic geometric spread layout
                if (metadata.spread_type === 'celtic') {
                    // Authentic Celtic Cross: Center Solar Cross (6 cards) + Right Ascending Staff (4 cards)
                    const altar = document.createElement('div');
                    altar.className = 'celtic-cross-altar';

                    // Solar Cross / Circle (Left Section)
                    const circle = document.createElement('div');
                    circle.className = 'celtic-cross-circle';

                    // 4: Above / Crown
                    if (metadata.cards[4]) {
                        circle.appendChild(makeCardEl(metadata.cards[4], metadata.positions[4] || 'Above', 4, 'celtic-pos-above'));
                    }
                    // 2: Past
                    if (metadata.cards[2]) {
                        circle.appendChild(makeCardEl(metadata.cards[2], metadata.positions[2] || 'Past', 2, 'celtic-pos-past'));
                    }
                    // Center Stack (0: Present & 1: Challenge)
                    const centerStack = document.createElement('div');
                    centerStack.className = 'celtic-center-stack';
                    if (metadata.cards[0]) {
                        centerStack.appendChild(makeCardEl(metadata.cards[0], metadata.positions[0] || 'Present', 0, 'celtic-card-present'));
                    }
                    if (metadata.cards[1]) {
                        centerStack.appendChild(makeCardEl(metadata.cards[1], metadata.positions[1] || 'Challenge', 1, 'celtic-card-challenge'));
                    }
                    circle.appendChild(centerStack);

                    // 3: Future
                    if (metadata.cards[3]) {
                        circle.appendChild(makeCardEl(metadata.cards[3], metadata.positions[3] || 'Future', 3, 'celtic-pos-future'));
                    }
                    // 5: Below / Foundation
                    if (metadata.cards[5]) {
                        circle.appendChild(makeCardEl(metadata.cards[5], metadata.positions[5] || 'Below', 5, 'celtic-pos-below'));
                    }
                    altar.appendChild(circle);

                    // Ascending Staff: Outcome (9) at top, down to Advice (6) at bottom
                    const staff = document.createElement('div');
                    staff.className = 'celtic-staff';
                    [9, 8, 7, 6].forEach(idx => {
                        if (metadata.cards[idx]) {
                            staff.appendChild(makeCardEl(metadata.cards[idx], metadata.positions[idx] || `Card ${idx + 1}`, idx));
                        }
                    });
                    altar.appendChild(staff);
                    visualStageCard.appendChild(altar);

                } else if (metadata.spread_type === '5-card') {
                    // Sacred 5-Card Cross (Center Present, North Challenge, West Past, East Future, South Outcome)
                    const container = document.createElement('div');
                    container.className = 'tarot-stage-grid layout-5-card';
                    metadata.cards.forEach((card, i) => {
                        container.appendChild(makeCardEl(card, metadata.positions[i] || `Card ${i + 1}`, i));
                    });
                    visualStageCard.appendChild(container);

                } else if (metadata.spread_type === '3-card') {
                    // 3-Card Triad (Past, Present, Future - strictly horizontal, never wraps)
                    const container = document.createElement('div');
                    container.className = 'tarot-stage-grid layout-3-card';
                    metadata.cards.forEach((card, i) => {
                        container.appendChild(makeCardEl(card, metadata.positions[i] || `Card ${i + 1}`, i));
                    });
                    visualStageCard.appendChild(container);

                } else {
                    // Standard / Single Card
                    const container = document.createElement('div');
                    container.className = 'tarot-stage-grid layout-single';
                    metadata.cards.forEach((card, i) => {
                        container.appendChild(makeCardEl(card, metadata.positions[i] || `Card ${i + 1}`, i));
                    });
                    visualStageCard.appendChild(container);
                }

                // Add altar orientation hint
                const hint = document.createElement('div');
                hint.className = 'altar-orientation-hint';
                hint.innerHTML = 'Select a card to explore it';
                visualStageCard.appendChild(hint);

            } else if (metadata.type === 'iching' && metadata.hexagram) {
                sounds.coinClatter();
                const hex = metadata.hexagram;

                const stageWrap = document.createElement('div');
                stageWrap.className = 'iching-stage-container';

                // Header
                stageWrap.innerHTML = `
                    <div class="iching-board-header">
                        <span>☯</span> THE BOOK OF CHANGES · I CHING <span>☯</span>
                    </div>
                `;

                // Helper to render a hexagram pillar
                const buildHexPillar = (hexData, roleTitle, isPrimary) => {
                    const pillar = document.createElement('div');
                    pillar.className = `hex-pillar ${isPrimary ? 'primary' : 'transformed'}`;

                    const upper = hexData.upper_trigram || {};
                    const lower = hexData.lower_trigram || {};

                    // Stack lines from Line 6 down to Line 1 (top to bottom visual layout)
                    let linesHtml = '';
                    const lineVals = hexData.lines || [7, 8, 7, 8, 7, 8];
                    for (let i = 5; i >= 0; i--) {
                        const val = lineVals[i];
                        const lineNum = i + 1;
                        const isYang = (val === 7 || val === 9);
                        const isChanging = (val === 6 || val === 9);

                        let barHtml = '';
                        if (isYang) {
                            barHtml = `<div class="hex-line-bar solid" title="Line ${lineNum}: Solid Yang Bar"></div>`;
                        } else {
                            barHtml = `
                                <div class="hex-line-bar broken" title="Line ${lineNum}: Broken Yin Bar">
                                    <span class="bar-segment"></span>
                                    <span class="bar-segment"></span>
                                </div>
                            `;
                        }

                        let tagHtml = '';
                        if (val === 9) {
                            tagHtml = `<div class="hex-changing-tag old-yang" title="Line ${lineNum}: Old Yang (9) — Changing into Yin">○</div>`;
                        } else if (val === 6) {
                            tagHtml = `<div class="hex-changing-tag old-yin" title="Line ${lineNum}: Old Yin (6) — Changing into Yang">×</div>`;
                        } else if (!isPrimary && hex.changing_lines && hex.changing_lines.includes(lineNum)) {
                            tagHtml = `<div class="hex-changing-tag transformed-indicator" title="Line ${lineNum}: Transformed Line">✦</div>`;
                        } else {
                            tagHtml = `<div class="hex-changing-tag static">•</div>`;
                        }

                        linesHtml += `
                            <div class="hex-line-row ${isChanging ? 'changing' : ''}">
                                <span class="hex-line-num">L${lineNum}</span>
                                ${barHtml}
                                ${tagHtml}
                            </div>
                        `;
                    }

                    pillar.innerHTML = `
                        <div class="hex-pillar-badge">${roleTitle}</div>
                        <div class="hex-pillar-head">
                            <div class="hex-pillar-name">Hexagram ${hexData.number}</div>
                            <div class="hex-pillar-chinese">${hexData.name} ${hexData.chinese ? `· ${hexData.chinese}` : ''}</div>
                        </div>
                        <div class="hex-trigrams-box">
                            <div class="trigram-chip" title="Upper Trigram: Outer Realm & Action">
                                <span class="tg-sym">${upper.symbol || '☰'}</span>
                                <span class="tg-label">Upper: ${upper.name || 'Upper'}</span>
                            </div>
                            <span class="trigram-divider">over</span>
                            <div class="trigram-chip" title="Lower Trigram: Inner Ground & Core">
                                <span class="tg-sym">${lower.symbol || '☰'}</span>
                                <span class="tg-label">Lower: ${lower.name || 'Lower'}</span>
                            </div>
                        </div>
                        <div class="hex-lines-stack">
                            ${linesHtml}
                        </div>
                        <div class="hex-pillar-footer">
                            <em>${hexData.meaning || ''}</em>
                            ${hexData.keywords ? `<div style="color: var(--text-muted); font-size: 11px; margin-top: 4px;">${hexData.keywords}</div>` : ''}
                        </div>
                    `;
                    return pillar;
                };

                // Pillars Row
                const pillarsRow = document.createElement('div');
                pillarsRow.className = 'iching-pillars-row';

                const hasChanging = hex.changing_lines && hex.changing_lines.length > 0 && hex.transformed;

                if (hasChanging) {
                    // Left: Primary Hexagram
                    pillarsRow.appendChild(buildHexPillar(hex, '本卦 · Primary Hexagram', true));

                    // Center: Energetic Transformation Bridge
                    const bridge = document.createElement('div');
                    bridge.className = 'iching-transform-bridge';
                    bridge.innerHTML = `
                        <div class="bridge-arrow-wrap" title="Celestial Transformation Energy">
                            <span class="bridge-arrow">➔</span>
                        </div>
                        <div class="bridge-label">Changing Lines</div>
                        <div class="bridge-lines-list">Lines ${hex.changing_lines.join(', ')}</div>
                    `;
                    pillarsRow.appendChild(bridge);

                    // Right: Transformed Hexagram
                    pillarsRow.appendChild(buildHexPillar(hex.transformed, '之卦 · Resulting Hexagram', false));
                } else {
                    // Single Steadfast Pillar
                    pillarsRow.appendChild(buildHexPillar(hex, '定卦 · Steadfast / Immutable', true));
                }

                stageWrap.appendChild(pillarsRow);

                // Ancient Bronze Coins Tray
                const coinsTray = document.createElement('div');
                coinsTray.className = 'iching-coins-tray';
                coinsTray.innerHTML = `
                    <div class="coins-tray-title">Ritual Three-Coin Cast · 三錢筮法</div>
                    <div class="coins-row">
                        <div class="ancient-bronze-coin" title="Ancient Han/Zhou Bronze Oracle Coin">
                            <span class="coin-glyph top">乾</span>
                            <span class="coin-glyph bottom">坤</span>
                            <span class="coin-glyph left">易</span>
                            <span class="coin-glyph right">道</span>
                            <div class="coin-center-hole"></div>
                        </div>
                        <div class="ancient-bronze-coin" title="Ancient Han/Zhou Bronze Oracle Coin">
                            <span class="coin-glyph top">乾</span>
                            <span class="coin-glyph bottom">坤</span>
                            <span class="coin-glyph left">易</span>
                            <span class="coin-glyph right">道</span>
                            <div class="coin-center-hole"></div>
                        </div>
                        <div class="ancient-bronze-coin" title="Ancient Han/Zhou Bronze Oracle Coin">
                            <span class="coin-glyph top">乾</span>
                            <span class="coin-glyph bottom">坤</span>
                            <span class="coin-glyph left">易</span>
                            <span class="coin-glyph right">道</span>
                            <div class="coin-center-hole"></div>
                        </div>
                    </div>
                `;
                stageWrap.appendChild(coinsTray);

                visualStageCard.appendChild(stageWrap);

            } else if (metadata.type === 'runes' && metadata.runes) {
                activeRuneSpread = metadata;
                sounds.chime();
                const mat = document.createElement('div');
                const spreadKey = metadata.spread_type || 'norns';
                mat.className = `rune-casting-mat layout-${spreadKey}`;
                const spreadHeader = metadata.spread_name ? `&#5855; ${metadata.spread_name.toUpperCase()} &#5855;` : '&#5855; SACRED RUNIC CASTING CLOTH &#5855;';
                mat.innerHTML = `<div class="rune-casting-mat-header">${spreadHeader}</div>`;

                const frostRunes = ['hagalaz', 'nauthiz', 'isa', 'jera', 'eihwaz', 'perthro', 'algiz', 'sowilo'];
                const amethystRunes = ['tiwaz', 'berkano', 'ehwaz', 'mannaz', 'laguz', 'ingwaz', 'dagaz', 'othala'];

                metadata.runes.forEach((rune, i) => {
                    const wrap = document.createElement('div');
                    wrap.className = 'rune-stone-wrapper';
                    wrap.setAttribute('data-index', i);
                    const position = (metadata.positions && metadata.positions[i]) || `Rune ${i + 1}`;
                    const runeKey = (rune.key || rune.name.toLowerCase()).replace(/[^a-z0-9]+/g, '');
                    const isRev = Boolean(rune.is_reversed);
                    if (isRev) wrap.classList.add('is-reversed');

                    // Natural random tilt between -5 and +5 degrees
                    const randomTilt = ((Math.random() * 10) - 5).toFixed(1);
                    wrap.style.transform = `rotate(${randomTilt}deg)`;

                    let aettClass = '';
                    if (frostRunes.includes(runeKey)) aettClass = 'frost';
                    else if (amethystRunes.includes(runeKey)) aettClass = 'amethyst';

                    const badgeClass = isRev ? 'badge-merkstave' : 'badge-upright';
                    const orientationLabel = isRev ? 'ᛦ Merkstave' : 'ᛚ Upright';
                    const meaningText = rune.active_meaning || rune.meaning;

                    wrap.innerHTML = `
                        <img src="/static/runes/${runeKey}.webp" 
                             alt="${rune.name}" 
                             class="rune-artifact-img ${isRev ? 'is-reversed' : ''}"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                        <div class="rune-stone-pebble" style="display: none;">
                            <div class="pebble-glyph ${aettClass}">${rune.symbol}</div>
                        </div>
                        <div class="rune-stone-meta">
                            <div class="rune-pos-badge ${badgeClass}">${position} • ${orientationLabel}</div>
                            <div class="rune-name-label">${rune.name} ${isRev ? '<span style="color:#fca5a5; font-size:12px;">(Merkstave)</span>' : ''}</div>
                            <div class="rune-meaning-label">${meaningText}</div>
                        </div>
                    `;

                    // 3D physical object parallax tilt on hover
                    wrap.addEventListener('mousemove', (e) => {
                        const rect = wrap.getBoundingClientRect();
                        const x = (e.clientX - rect.left) / rect.width - 0.5;
                        const y = (e.clientY - rect.top) / rect.height - 0.5;
                        const rotX = (-y * 22).toFixed(2);
                        const rotY = (x * 22).toFixed(2);
                        const stoneEl = wrap.querySelector('.rune-artifact-img:not([style*="display: none"])') || wrap.querySelector('.rune-stone-pebble');
                        if (stoneEl) {
                            stoneEl.style.transform = `perspective(500px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale3d(1.08, 1.08, 1.08) translateZ(14px)`;
                        }
                    });

                    wrap.addEventListener('mouseleave', () => {
                        const stoneEl = wrap.querySelector('.rune-artifact-img') || wrap.querySelector('.rune-stone-pebble');
                        if (stoneEl) {
                            stoneEl.style.transition = 'transform 0.35s ease';
                            stoneEl.style.transform = '';
                            setTimeout(() => { stoneEl.style.transition = ''; }, 350);
                        }
                    });

                    wrap.setAttribute('role', 'button');
                    wrap.tabIndex = 0;
                    wrap.setAttribute('aria-label', `${metadata.positions?.[i] || 'Rune ' + (i + 1)}: ${rune.name}. View rune`);
                    wrap.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openRuneZoom(i); } });
                    wrap.addEventListener('click', () => {
                        openRuneZoom(i);
                    });

                    mat.appendChild(wrap);
                    setTimeout(() => sounds.stoneClack(), i * 180);
                });
                visualStageCard.appendChild(mat);

                const hint = document.createElement('div');
                hint.className = 'altar-orientation-hint';
                hint.innerHTML = 'Select a rune to explore it';
                visualStageCard.appendChild(hint);

            } else if (metadata.quantum_number) {
                sounds.chime();
                visualStageCard.innerHTML = `
                    <div class="number-stage">
                        <span style="font-size: 15px; color: var(--text-muted);">Your number</span>
                        <div class="number-value">${metadata.quantum_number}</div>
                    </div>
                `;
            }
        }

        // ==========================================
        // Social Share Card & Talisman Generator
        // The card is composited on a <canvas>, so the on-screen preview is
        // pixel-identical to the exported PNG. html2canvas is only used to
        // photograph the live altar; all cropping / fitting is done here.
        // ==========================================
        let currentSocialFormat = 'story'; // 'story' (9:16) or 'post' (1:1)
        let socialCandidateQuotes = [];
        let activeQuoteIndex = 0;
        let talismanSnapshot = null;   // { canvas, content: {x, y, w, h} } — altar render + tight spread bounds (canvas px)
        let talismanRenderSeq = 0;
        let talismanRenderTimer = null;
        let talismanPreviewUrl = null;
        let talismanFontsReady = null;

        const TALISMAN_FORMATS = {
            story: { w: 1080, h: 1920, label: '1080 × 1920 · PNG' },
            post:  { w: 1080, h: 1080, label: '1080 × 1080 · PNG' }
        };
        // Per tradition: elements whose union defines "the spread", and (optionally) the surface whose
        // texture the crop may extend over. Runes crop to the stones but never past the casting cloth.
        const TALISMAN_CONTENT_RULES = [
            { content: '.tarot-card-wrapper', clamp: null },
            { content: '.rune-stone-wrapper', clamp: '.rune-casting-mat' },
            { content: '.iching-stage-container > *', clamp: null },
            { content: '.number-stage', clamp: null }
        ];
        const TALISMAN_SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif";
        const TALISMAN_DISPLAY = "'Cinzel', 'Cormorant Garamond', Georgia, serif";
        const TALISMAN_SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

        function downloadCanvas(canvas, filename) {
            const link = document.createElement('a');
            link.download = filename;
            link.href = canvas.toDataURL('image/png');
            link.click();
        }

        async function exportActiveReading() {
            const el = document.getElementById('visual-stage-card');
            if (!el) return;
            el.classList.add('is-capturing');
            try {
                const canvas = await html2canvas(el, { backgroundColor: '#12111a', scale: 2, useCORS: true, logging: false });
                downloadCanvas(canvas, 'oracle-altar.png');
            } catch (e) {
                alert('Could not generate image. Please take a screenshot instead.');
            } finally {
                el.classList.remove('is-capturing');
            }
        }

        // Pulls the most quotable lines out of the rendered reading.
        function extractCandidateQuotes(sourceEl) {
            const fallback = ["A moment of insight. A new perspective."];
            if (!sourceEl) return fallback;
            const rawText = sourceEl.innerText || '';
            if (!rawText.trim()) return fallback;

            const candidates = [];
            const push = (s) => {
                const clean = (s || '')
                    .replace(/\s+/g, ' ')
                    .replace(/^[A-Za-z✦·—-]+(?:\s[A-Za-z✦·—-]+){0,3}:\s+/, '')
                    .replace(/^["“]+|["”]+$/g, '')
                    .trim();
                if (clean.length >= 25 && clean.length <= 280 && !candidates.includes(clean)) candidates.push(clean);
            };

            // 1. The Oracle's own emphasised prophecies are the most shareable lines
            sourceEl.querySelectorAll('strong, b').forEach(el => {
                if (el.closest('h1, h2, h3, h4')) return;
                push(el.textContent);
            });

            // 2. Evocative sentences, scanning from the closing synthesis backwards
            const sentences = rawText
                .replace(/[#*`_>]/g, '')
                .split(/(?<=[.?!])\s+/)
                .map(s => s.trim())
                .filter(s => s.length >= 30 && s.length <= 260 && !/^[-•✦]/.test(s) && !s.startsWith('http'));

            const keywordRegex = /(path|destiny|courage|omen|wisdom|transform|balance|inner|lesson|clarity|truth|horizon|guide|step|spirit|action|yield|illumination|trust|release|become)/i;
            for (let i = sentences.length - 1; i >= 0 && candidates.length < 4; i--) {
                if (keywordRegex.test(sentences[i])) push(sentences[i]);
            }

            // 3. Plain sentences if we are still short
            for (const s of sentences) {
                if (candidates.length >= 3) break;
                push(s);
            }

            if (candidates.length === 0) {
                candidates.push(rawText.trim().slice(0, 280));
            }
            return candidates.slice(0, 4);
        }

        function getReadingSpreadTitle(tradition, data) {
            const trad = (data && data.type) || tradition || currentTradition || 'tarot';
            if (trad === 'tarot') {
                const spread = (data && data.spread_type) || currentSpreadType || '3-card';
                const map = {
                    'celtic': 'Celtic Cross Tarot',
                    '3-card': 'Three-Card Tarot',
                    '5-card': 'Five-Card Cross Tarot',
                    'yes-no': 'Single Card Tarot'
                };
                return (map[spread] || 'Tarot Reading').toUpperCase();
            } else if (trad === 'runes') {
                if (data && data.spread_name) return data.spread_name.toUpperCase();
                const spread = (data && data.spread_type) || currentSpreadType || 'norns';
                const map = {
                    'norns': 'Three Norns Runic Spread',
                    'single': "Odin's Single Rune Cast",
                    'five-cross': 'Five-Rune Wyrd Cross',
                    'thor-hammer': "Thor's Hammer Runic Cast",
                    'nine-worlds': 'Nine Worlds of Yggdrasil'
                };
                return (map[spread] || 'Elder Futhark Runes').toUpperCase();
            } else if (trad === 'iching') {
                if (data && data.hexagram && data.hexagram.name) {
                    return `Hexagram ${data.hexagram.number || ''}: ${data.hexagram.name}`.toUpperCase();
                }
                return 'The I Ching · Book of Changes'.toUpperCase();
            } else if (trad === 'number' || trad === 'oracle') {
                return 'Numerology Reading'.toUpperCase();
            }
            return 'Quantum Divination'.toUpperCase();
        }

        function ensureTalismanFonts() {
            if (!talismanFontsReady) {
                talismanFontsReady = (document.fonts && document.fonts.load)
                    ? Promise.all([
                        document.fonts.load('700 48px "Cormorant Garamond"'),
                        document.fonts.load('600 24px Cinzel')
                    ]).catch(() => {})
                    : Promise.resolve();
            }
            return talismanFontsReady;
        }

        // Photographs the live altar once per share session. Returns the raw stage render plus the
        // tight bounding box of the spread itself, so the compositor can place every card without
        // cropping or distortion regardless of the card format's aspect ratio.
        async function captureAltarSnapshot() {
            const stage = document.getElementById('visual-stage-card');
            if (!stage || typeof html2canvas !== 'function') return null;

            stage.classList.add('is-capturing', 'is-capturing-bare');
            try {
                void stage.offsetHeight; // reflow after hiding the hint so measurements match the capture
                const stageRect = stage.getBoundingClientRect();
                const union = (a, r) => a
                    ? { left: Math.min(a.left, r.left), top: Math.min(a.top, r.top), right: Math.max(a.right, r.right), bottom: Math.max(a.bottom, r.bottom) }
                    : { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
                let box = null;
                const stageInset = 4; // stay inside the altar's 2px border
                let clampRect = { left: stageRect.left + stageInset, top: stageRect.top + stageInset, right: stageRect.right - stageInset, bottom: stageRect.bottom - stageInset };
                for (const rule of TALISMAN_CONTENT_RULES) {
                    const els = stage.querySelectorAll(rule.content);
                    if (!els.length) continue;
                    els.forEach(el => {
                        const r = el.getBoundingClientRect();
                        if (r.width >= 2 && r.height >= 2) box = union(box, r);
                    });
                    if (!box) continue;
                    const clampEl = rule.clamp ? stage.querySelector(rule.clamp) : null;
                    if (clampEl) {
                        const c = clampEl.getBoundingClientRect();
                        const inset = 6; // stay inside the surface's border
                        clampRect = {
                            left: Math.max(clampRect.left, c.left + inset), top: Math.max(clampRect.top, c.top + inset),
                            right: Math.min(clampRect.right, c.right - inset), bottom: Math.min(clampRect.bottom, c.bottom - inset)
                        };
                    }
                    break;
                }
                if (!box) box = { left: stageRect.left, top: stageRect.top, right: stageRect.right, bottom: stageRect.bottom };

                // Breathing room of altar texture around the spread, clamped to its surface
                const padX = (box.right - box.left) * 0.06 + 10;
                const padY = (box.bottom - box.top) * 0.06 + 10;
                const left = Math.max(clampRect.left, box.left - padX);
                const top = Math.max(clampRect.top, box.top - padY);
                const right = Math.min(clampRect.right, box.right + padX);
                const bottom = Math.min(clampRect.bottom, box.bottom + padY);

                // Render scale: enough pixels that the spread stays crisp at 1080px export, capped for memory
                const longSide = Math.max(1, right - left, bottom - top);
                let scale = Math.max(2, 1300 / longSide);
                scale = Math.min(scale, 4, Math.sqrt(14e6 / Math.max(1, stageRect.width * stageRect.height)));

                const canvas = await html2canvas(stage, {
                    backgroundColor: null,
                    scale,
                    useCORS: true,
                    logging: false
                });

                return {
                    canvas,
                    content: {
                        x: (left - stageRect.left) * scale,
                        y: (top - stageRect.top) * scale,
                        w: (right - left) * scale,
                        h: (bottom - top) * scale
                    }
                };
            } catch (e) {
                console.warn('Could not snapshot visual stage:', e);
                return null;
            } finally {
                stage.classList.remove('is-capturing', 'is-capturing-bare');
            }
        }

        // ---------- Canvas typesetting helpers ----------
        function talismanFont(weight, size, family) {
            return `${weight} ${size}px ${family}`;
        }

        // Centered text with letter-spacing (native where supported, manual otherwise)
        function drawTrackedText(ctx, text, cx, y, tracking) {
            if ('letterSpacing' in ctx) {
                ctx.letterSpacing = `${tracking}px`;
                ctx.textAlign = 'center';
                ctx.fillText(text, cx + tracking / 2, y);
                ctx.letterSpacing = '0px';
                return;
            }
            const chars = [...text];
            const widths = chars.map(c => ctx.measureText(c).width);
            const total = widths.reduce((a, b) => a + b, 0) + tracking * (chars.length - 1);
            let x = cx - total / 2;
            ctx.textAlign = 'left';
            chars.forEach((c, i) => {
                ctx.fillText(c, x, y);
                x += widths[i] + tracking;
            });
        }

        function wrapLines(ctx, text, maxWidth) {
            const words = text.split(/\s+/).filter(Boolean);
            const lines = [];
            let line = '';
            for (const word of words) {
                const test = line ? `${line} ${word}` : word;
                if (!line || ctx.measureText(test).width <= maxWidth) {
                    line = test;
                } else {
                    lines.push(line);
                    line = word;
                }
            }
            if (line) lines.push(line);
            return lines;
        }

        // Re-wraps at narrower widths (same line count) so line lengths are even and no orphans dangle
        function balanceLines(ctx, text, maxWidth, lines) {
            if (lines.length < 2) return lines;
            const spreadOf = (ls) => {
                const ws = ls.map(l => ctx.measureText(l).width);
                return Math.max(...ws) - Math.min(...ws);
            };
            let best = lines;
            let bestSpread = spreadOf(lines);
            for (let f = 0.97; f >= 0.7; f -= 0.03) {
                const cand = wrapLines(ctx, text, maxWidth * f);
                if (cand.length !== lines.length) break;
                const s = spreadOf(cand);
                if (s < bestSpread) { best = cand; bestSpread = s; }
            }
            return best;
        }

        // Largest font size whose wrapped block fits the box → { size, lines, lineHeight }
        function fitQuote(ctx, text, maxWidth, maxHeight, maxSize, minSize, lhRatio) {
            for (let size = maxSize; size >= minSize; size -= 2) {
                ctx.font = talismanFont(700, size, TALISMAN_SERIF);
                const lines = wrapLines(ctx, text, maxWidth);
                const lh = Math.round(size * lhRatio);
                if (lines.length * lh <= maxHeight && lines.every(l => ctx.measureText(l).width <= maxWidth)) {
                    return { size, lines: balanceLines(ctx, text, maxWidth, lines), lineHeight: lh };
                }
            }
            // Does not fit even at the minimum: truncate gracefully
            ctx.font = talismanFont(700, minSize, TALISMAN_SERIF);
            const lines = wrapLines(ctx, text, maxWidth);
            const lh = Math.round(minSize * lhRatio);
            const maxLines = Math.max(1, Math.floor(maxHeight / lh));
            if (lines.length > maxLines) {
                lines.length = maxLines;
                let last = lines[maxLines - 1];
                while (last.length > 3 && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1).trimEnd();
                lines[maxLines - 1] = `${last.replace(/[,.;:\s]+$/, '')}…`;
            }
            return { size: minSize, lines, lineHeight: lh };
        }

        // ---------- Canvas image helpers ----------
        // Soft, colour-matched ambient fill: cover-crop of the spread, blurred via progressive downscale
        function drawAmbientFill(ctx, snap, W, H) {
            const { canvas: src, content: c } = snap;
            const targetAspect = W / H;
            let sx = c.x, sy = c.y, sw = c.w, sh = c.h;
            if (sw / sh > targetAspect) {
                sw = sh * targetAspect;
                sx = c.x + (c.w - sw) / 2;
            } else {
                sh = sw / targetAspect;
                sy = c.y + (c.h - sh) / 2;
            }
            const small = document.createElement('canvas');
            small.width = 12;
            small.height = Math.max(1, Math.round(12 / targetAspect));
            const sctx = small.getContext('2d');
            sctx.imageSmoothingEnabled = true;
            sctx.imageSmoothingQuality = 'high';
            sctx.drawImage(src, sx, sy, sw, sh, 0, 0, small.width, small.height);

            const mid = document.createElement('canvas');
            mid.width = 72;
            mid.height = Math.max(1, Math.round(72 / targetAspect));
            const mctx = mid.getContext('2d');
            mctx.imageSmoothingEnabled = true;
            mctx.imageSmoothingQuality = 'high';
            mctx.drawImage(small, 0, 0, mid.width, mid.height);

            ctx.save();
            ctx.globalAlpha = 0.88;
            const over = 1.08;
            ctx.drawImage(mid, -(W * (over - 1)) / 2, -(H * (over - 1)) / 2, W * over, H * over);
            ctx.restore();
        }

        function drawFallbackAmbient(ctx, W, H) {
            const g = ctx.createRadialGradient(W / 2, H * 0.45, 0, W / 2, H * 0.45, Math.max(W, H) * 0.7);
            g.addColorStop(0, 'rgba(120, 82, 40, 0.55)');
            g.addColorStop(0.5, 'rgba(40, 24, 50, 0.6)');
            g.addColorStop(1, 'rgba(8, 6, 18, 1)');
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, W, H);
        }

        function talismanRoundRect(ctx, x, y, w, h, r) {
            const rr = Math.max(0, Math.min(r, w / 2, h / 2));
            ctx.beginPath();
            ctx.moveTo(x + rr, y);
            ctx.lineTo(x + w - rr, y);
            ctx.arcTo(x + w, y, x + w, y + rr, rr);
            ctx.lineTo(x + w, y + h - rr);
            ctx.arcTo(x + w, y + h, x + w - rr, y + h, rr);
            ctx.lineTo(x + rr, y + h);
            ctx.arcTo(x, y + h, x, y + h - rr, rr);
            ctx.lineTo(x, y + rr);
            ctx.arcTo(x, y, x + rr, y, rr);
            ctx.closePath();
        }

        // Draws the spread at its true aspect ratio as a framed altar photograph: rounded corners,
        // a gold hairline and a soft drop shadow over the blurred backdrop.
        function drawFramedArt(ctx, snap, art, radius) {
            const { canvas: src, content: c } = snap;
            const x = Math.round(art.x);
            const y = Math.round(art.y);
            const w = Math.round(art.w);
            const h = Math.round(art.h);
            if (w < 2 || h < 2) return;

            ctx.save();
            ctx.shadowColor = 'rgba(0, 0, 0, 0.7)';
            ctx.shadowBlur = 54;
            ctx.shadowOffsetY = 22;
            ctx.fillStyle = '#0a0812';
            talismanRoundRect(ctx, x, y, w, h, radius);
            ctx.fill();
            ctx.restore();

            ctx.save();
            talismanRoundRect(ctx, x, y, w, h, radius);
            ctx.clip();
            ctx.drawImage(src, c.x, c.y, c.w, c.h, x, y, w, h);
            ctx.restore();

            ctx.save();
            ctx.strokeStyle = 'rgba(229, 193, 88, 0.34)';
            ctx.lineWidth = 2;
            talismanRoundRect(ctx, x + 1, y + 1, w - 2, h - 2, Math.max(0, radius - 1));
            ctx.stroke();
            ctx.restore();
        }

        // ---------- Layout ----------
        // Story: header / spread / quote stacked inside Instagram's safe zones.
        // Post: stacked for wide spreads, side-by-side for tall spreads (single card, 5-card cross).
        function computeTalismanLayout(ctx, format, W, H, snap, quote) {
            const isStory = format === 'story';
            const aspect = snap ? snap.content.w / Math.max(1, snap.content.h) : 1;
            const L = {
                W, H, isStory,
                headerY: isStory ? 250 : 92,
                footerY: isStory ? H - 250 : H - 72,
                art: null,
                quote: null
            };
            const contentTop = isStory ? 300 : 156;
            const contentBottom = isStory ? H - 330 : H - 150;
            const zoneH = contentBottom - contentTop;
            const attrH = isStory ? 24 : 20;
            const attrGap = isStory ? 40 : 30;

            if (!isStory && snap && aspect < 1.2) {
                // Side-by-side square post
                const margin = 64;
                const colGap = 44;
                const artColW = 470;
                let aw = artColW;
                let ah = aw / aspect;
                if (ah > zoneH) { ah = zoneH; aw = ah * aspect; }
                L.art = { x: margin + (artColW - aw) / 2, y: contentTop + (zoneH - ah) / 2, w: aw, h: ah };

                const qx0 = margin + artColW + colGap;
                const qw = W - margin - qx0;
                const fit = fitQuote(ctx, quote, qw, zoneH - attrGap - attrH, 46, 26, 1.22);
                const quoteH = fit.lines.length * fit.lineHeight;
                const blockH = quoteH + attrGap + attrH;
                const top = contentTop + (zoneH - blockH) / 2;
                L.quote = { cx: qx0 + qw / 2, top, width: qw, fit, attrY: top + quoteH + attrGap + attrH * 0.75 };
                return L;
            }

            // Stacked, art first: the quote is set at a comfortable size (bounded), the spread takes the
            // rest. Very long quotes shrink toward the floor rather than squeezing the cards below a minimum.
            // Tall spreads (single card, five-card cross, Celtic Cross) are height-bound in a story,
            // so the quote yields more height to them than it does for wide spreads.
            const tall = snap && aspect < 0.85;
            const artMaxW = isStory ? 940 : 960;
            const artCapH = isStory ? 1060 : 540;
            const artMinH = isStory ? 560 : 300;
            const artGap = isStory ? 52 : 48;
            const quoteMaxW = isStory ? 900 : 920;
            const quoteMaxSize = isStory ? (tall ? 56 : 62) : 50;
            const quoteMinSize = isStory ? 40 : 28;
            const quoteBlockCap = isStory ? (tall ? 270 : 330) : 240;

            let fit = fitQuote(ctx, quote, quoteMaxW, quoteBlockCap, quoteMaxSize, quoteMinSize, 1.22);
            let quoteH = fit.lines.length * fit.lineHeight;
            let art = null;
            if (snap) {
                let availArtH = zoneH - quoteH - attrGap - attrH - artGap;
                if (availArtH < artMinH) {
                    fit = fitQuote(ctx, quote, quoteMaxW, Math.max(80, zoneH - artMinH - artGap - attrGap - attrH), quoteMaxSize, quoteMinSize, 1.22);
                    quoteH = fit.lines.length * fit.lineHeight;
                    availArtH = zoneH - quoteH - attrGap - attrH - artGap;
                }
                let ah = Math.min(artCapH, Math.max(artMinH, availArtH));
                let aw = ah * aspect;
                if (aw > artMaxW) { aw = artMaxW; ah = aw / aspect; }
                art = { w: aw, h: ah };
            }
            const groupH = (art ? art.h + artGap : 0) + quoteH + attrGap + attrH;
            let y = contentTop + Math.max(0, (zoneH - groupH) * 0.42); // optical centre sits slightly high
            if (art) {
                L.art = { x: (W - art.w) / 2, y, w: art.w, h: art.h };
                y += art.h + artGap;
            }
            L.quote = { cx: W / 2, top: y, width: quoteMaxW, fit, attrY: y + quoteH + attrGap + attrH * 0.75 };
            return L;
        }

        function drawTalismanType(ctx, L, title, quote) {
            const { isStory } = L;
            ctx.textBaseline = 'alphabetic';

            // Header: spread name
            ctx.save();
            ctx.font = talismanFont(600, isStory ? 27 : 23, TALISMAN_SANS);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.74)';
            ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
            ctx.shadowBlur = 12;
            ctx.shadowOffsetY = 2;
            drawTrackedText(ctx, title, L.W / 2, L.headerY, isStory ? 7 : 6);
            ctx.restore();

            // Quote
            const q = L.quote;
            ctx.save();
            ctx.font = talismanFont(700, q.fit.size, TALISMAN_SERIF);
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.shadowColor = 'rgba(0, 0, 0, 0.95)';
            ctx.shadowBlur = 22;
            ctx.shadowOffsetY = 3;
            let y = q.top + q.fit.size * 0.82;
            q.fit.lines.forEach(line => {
                ctx.fillText(line, q.cx, y);
                y += q.fit.lineHeight;
            });
            ctx.restore();

            // Attribution
            ctx.save();
            ctx.font = talismanFont(600, isStory ? 21 : 18, TALISMAN_DISPLAY);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.78)';
            ctx.shadowColor = 'rgba(0, 0, 0, 0.9)';
            ctx.shadowBlur = 10;
            ctx.shadowOffsetY = 2;
            drawTrackedText(ctx, '— THE QUANTUM ORACLE', q.cx, q.attrY, isStory ? 5 : 4);
            ctx.restore();

            // Footer domain watermark
            ctx.save();
            ctx.font = talismanFont(300, isStory ? 28 : 24, TALISMAN_SANS);
            ctx.fillStyle = 'rgba(255, 255, 255, 0.56)';
            ctx.shadowColor = 'rgba(0, 0, 0, 0.8)';
            ctx.shadowBlur = 8;
            ctx.shadowOffsetY = 1;
            drawTrackedText(ctx, 'qoracle.app', L.W / 2, L.footerY, isStory ? 6 : 5);
            ctx.restore();
        }

        function getSocialQuoteText() {
            const quoteInput = document.getElementById('socialQuoteInput');
            const raw = (quoteInput && quoteInput.value.trim()) || 'The Oracle channels genuine quantum vacuum indeterminacy to illuminate your present horizon.';
            return raw.replace(/^["“]+|["”]+$/g, '').replace(/\s+/g, ' ').trim();
        }

        // Full-resolution composition of the share card
        function composeTalisman(format) {
            const spec = TALISMAN_FORMATS[format] || TALISMAN_FORMATS.story;
            const W = spec.w;
            const H = spec.h;
            const canvas = document.createElement('canvas');
            canvas.width = W;
            canvas.height = H;
            const ctx = canvas.getContext('2d');
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';

            const quote = getSocialQuoteText();
            const title = getReadingSpreadTitle(currentTradition, currentReadingData);
            const snap = talismanSnapshot;

            // 1. Ground + ambient colour drawn from the altar itself
            ctx.fillStyle = '#080612';
            ctx.fillRect(0, 0, W, H);
            if (snap) drawAmbientFill(ctx, snap, W, H);
            else drawFallbackAmbient(ctx, W, H);

            // 2. Darken so type stays legible, heavier at the top and bottom bands
            let g = ctx.createLinearGradient(0, 0, 0, H);
            g.addColorStop(0, 'rgba(6, 4, 14, 0.62)');
            g.addColorStop(0.35, 'rgba(6, 4, 14, 0.24)');
            g.addColorStop(0.7, 'rgba(6, 4, 14, 0.46)');
            g.addColorStop(1, 'rgba(6, 4, 14, 0.80)');
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, W, H);

            // 3. Layout, then the spread at true aspect ratio
            const L = computeTalismanLayout(ctx, format, W, H, snap, quote);
            if (snap && L.art) drawFramedArt(ctx, snap, L.art, L.isStory ? 30 : 26);

            // 4. Edge vignette to bind the composition
            const rg = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.42, W / 2, H / 2, Math.hypot(W, H) * 0.58);
            rg.addColorStop(0, 'rgba(4, 3, 8, 0)');
            rg.addColorStop(1, 'rgba(4, 3, 8, 0.62)');
            ctx.fillStyle = rg;
            ctx.fillRect(0, 0, W, H);

            // 5. Soft dark halo behind the quote block keeps type legible over bright ambient colour
            if (L.quote) {
                const q = L.quote;
                const qh = q.fit.lines.length * q.fit.lineHeight;
                const cy = q.top + qh / 2;
                const rx = q.width * 0.72;
                const ry = qh * 0.9 + 120;
                ctx.save();
                ctx.translate(q.cx, cy);
                ctx.scale(rx / ry, 1);
                const halo = ctx.createRadialGradient(0, 0, 0, 0, 0, ry);
                halo.addColorStop(0, 'rgba(6, 4, 14, 0.5)');
                halo.addColorStop(0.6, 'rgba(6, 4, 14, 0.28)');
                halo.addColorStop(1, 'rgba(6, 4, 14, 0)');
                ctx.fillStyle = halo;
                ctx.fillRect(-ry * 2, -ry, ry * 4, ry * 2);
                ctx.restore();
            }

            // 6. Type
            drawTalismanType(ctx, L, title, quote);
            return canvas;
        }

        // ---------- Preview & controls ----------
        function scheduleTalismanRender(delay = 200) {
            clearTimeout(talismanRenderTimer);
            talismanRenderTimer = setTimeout(renderTalismanPreview, delay);
        }

        async function renderTalismanPreview() {
            const frame = document.getElementById('talismanPreviewFrame');
            const img = document.getElementById('talismanPreviewImg');
            if (!frame || !img) return;
            const seq = ++talismanRenderSeq;
            frame.classList.add('is-rendering');
            try {
                await ensureTalismanFonts();
                if (seq !== talismanRenderSeq) return;
                const canvas = composeTalisman(currentSocialFormat);
                await new Promise(resolve => {
                    canvas.toBlob(blob => {
                        if (seq !== talismanRenderSeq || !blob) return resolve();
                        if (talismanPreviewUrl) URL.revokeObjectURL(talismanPreviewUrl);
                        talismanPreviewUrl = URL.createObjectURL(blob);
                        img.onload = () => {
                            frame.classList.remove('is-empty', 'is-rendering');
                            resolve();
                        };
                        img.onerror = () => {
                            frame.classList.remove('is-rendering');
                            resolve();
                        };
                        img.src = talismanPreviewUrl;
                    }, 'image/jpeg', 0.9);
                });
            } catch (e) {
                console.error('Talisman render failed:', e);
                frame.classList.remove('is-rendering');
            }
        }

        function setSocialFormat(format, opts = {}) {
            currentSocialFormat = format === 'post' ? 'post' : 'story';
            const storyBtn = document.getElementById('formatBtnStory');
            const postBtn = document.getElementById('formatBtnPost');
            const frame = document.getElementById('talismanPreviewFrame');
            const dims = document.getElementById('talismanPreviewDims');
            const isStory = currentSocialFormat === 'story';

            if (storyBtn) {
                storyBtn.classList.toggle('active', isStory);
                storyBtn.setAttribute('aria-pressed', String(isStory));
            }
            if (postBtn) {
                postBtn.classList.toggle('active', !isStory);
                postBtn.setAttribute('aria-pressed', String(!isStory));
            }
            if (frame) {
                frame.classList.remove('format-story', 'format-post');
                frame.classList.add(`format-${currentSocialFormat}`);
            }
            if (dims) dims.textContent = TALISMAN_FORMATS[currentSocialFormat].label;
            if (opts.render !== false) renderTalismanPreview();
        }

        function renderQuoteOptions() {
            const list = document.getElementById('quoteSelectorTabs');
            if (!list) return;
            list.innerHTML = '';
            socialCandidateQuotes.forEach((q, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `quote-option${idx === activeQuoteIndex ? ' active' : ''}`;
                const text = document.createElement('span');
                text.className = 'quote-option-text';
                text.textContent = q;
                btn.appendChild(text);
                btn.title = q;
                btn.setAttribute('aria-pressed', String(idx === activeQuoteIndex));
                btn.onclick = () => selectQuotePill(idx);
                list.appendChild(btn);
            });
        }

        function syncQuoteOptionState() {
            const options = document.querySelectorAll('#quoteSelectorTabs .quote-option');
            options.forEach((btn, idx) => {
                const on = idx === activeQuoteIndex;
                btn.classList.toggle('active', on);
                btn.setAttribute('aria-pressed', String(on));
            });
        }

        function selectQuotePill(index) {
            activeQuoteIndex = index;
            const quoteInput = document.getElementById('socialQuoteInput');
            if (quoteInput && socialCandidateQuotes[index] !== undefined) {
                quoteInput.value = socialCandidateQuotes[index];
            }
            syncQuoteOptionState();
            updateSocialQuoteCount();
            renderTalismanPreview();
        }

        function updateSocialQuoteCount() {
            const quoteInput = document.getElementById('socialQuoteInput');
            const counter = document.getElementById('socialQuoteCount');
            if (!quoteInput || !counter) return;
            const len = quoteInput.value.trim().length;
            const max = parseInt(quoteInput.getAttribute('maxlength'), 10) || 320;
            counter.textContent = `${len} / ${max}`;
            counter.classList.toggle('is-long', len > 200);
        }

        function onSocialQuoteInput() {
            const quoteInput = document.getElementById('socialQuoteInput');
            const value = quoteInput ? quoteInput.value.trim() : '';
            activeQuoteIndex = socialCandidateQuotes.indexOf(value);
            syncQuoteOptionState();
            updateSocialQuoteCount();
            scheduleTalismanRender(220);
        }

        async function openSocialExportModal() {
            initAudio();
            sounds.chime();

            const dialog = document.getElementById('socialExportModal');
            const feedback = document.getElementById('socialShareFeedback');
            const frame = document.getElementById('talismanPreviewFrame');
            if (feedback) feedback.textContent = '';
            if (frame) frame.classList.add('is-empty');

            // Quote candidates from the rendered reading
            socialCandidateQuotes = extractCandidateQuotes(oracleStreamText);
            activeQuoteIndex = 0;
            renderQuoteOptions();
            const quoteInput = document.getElementById('socialQuoteInput');
            if (quoteInput) quoteInput.value = socialCandidateQuotes[0] || '';
            updateSocialQuoteCount();
            setSocialFormat('story', { render: false });

            talismanSnapshot = null;
            // Open immediately with a weaving state, then photograph the altar behind the dialog
            if (dialog && !dialog.open) dialog.showModal();
            document.getElementById('socialNativeShareBtn').disabled = true;
            document.getElementById('socialDownloadBtn').disabled = true;
            try {
                talismanSnapshot = await captureAltarSnapshot();
                await renderTalismanPreview();
            } catch (error) {
                if (feedback) feedback.textContent = 'The image could not be prepared. Close this view and try again.';
            } finally {
                document.getElementById('socialNativeShareBtn').disabled = !talismanSnapshot;
                document.getElementById('socialDownloadBtn').disabled = !talismanSnapshot;
            }
        }

        function closeSocialExportModal() {
            const dialog = document.getElementById('socialExportModal');
            clearTimeout(talismanRenderTimer);
            if (dialog && dialog.open) dialog.close();
        }

        function socialFilename(format) {
            const title = getReadingSpreadTitle(currentTradition, currentReadingData)
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/(^-|-$)/g, '');
            return `qoracle-${title || 'reading'}-${format}.png`;
        }

        async function triggerSocialShare(mode) {
            const feedback = document.getElementById('socialShareFeedback');
            const shareBtn = document.getElementById('socialNativeShareBtn');
            const downloadBtn = document.getElementById('socialDownloadBtn');
            const setBusy = (busy) => {
                if (shareBtn) shareBtn.disabled = busy;
                if (downloadBtn) downloadBtn.disabled = busy;
            };
            const say = (msg) => { if (feedback) feedback.textContent = msg; };

            say('Preparing your image…');
            setBusy(true);
            sounds.cardFlip();

            const format = currentSocialFormat;
            const filename = socialFilename(format);

            try {
                await ensureTalismanFonts();
                const canvas = composeTalisman(format);
                const quoteText = getSocialQuoteText();

                if (mode === 'share' && navigator.share && navigator.canShare && canvas.toBlob) {
                    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
                    if (!blob) throw new Error('toBlob failed');
                    const file = new File([blob], filename, { type: 'image/png' });
                    if (navigator.canShare({ files: [file] })) {
                        try {
                            await navigator.share({
                                title: 'Quantum Oracle Divination',
                                text: `My divination reading from The Quantum Oracle: "${quoteText}" — qoracle.app`,
                                files: [file]
                            });
                            say('Image shared.');
                        } catch (err) {
                            if (err && err.name === 'AbortError') {
                                say('');
                            } else {
                                downloadCanvas(canvas, filename);
                                say('Image downloaded.');
                            }
                        }
                        return;
                    }
                }

                downloadCanvas(canvas, filename);
                say('Image downloaded.');
            } catch (e) {
                console.error(e);
                say('Could not generate image. Please take a screenshot instead.');
            } finally {
                setBusy(false);
            }
        }

        // Initialize App on Load
        window.addEventListener('DOMContentLoaded', () => {
            updateSpreadOptions();
            renderHistoryDrawer();

            // Demo URL query param handler for testing and showcase verification
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('demo')) {
                const demoType = urlParams.get('demo');
                portal.hidden = true;
                readingStage.hidden = false;
                if (demoType === 'iching') {
                    currentReadingData = {
                        type: 'iching',
                        hexagram: {
                            number: 38,
                            name: 'Opposition',
                            chinese: '睽 (Kuí)',
                            symbol: '☲☱',
                            meaning: 'Fire over Lake',
                            keywords: 'Creative divergence, unique vantage, finding harmony in difference',
                            upper_trigram: { symbol: '☲', name: 'Fire', element: 'Radiant Flame', nature: 'Clinging' },
                            lower_trigram: { symbol: '☱', name: 'Lake', element: 'Open Water', nature: 'Joyful' },
                            changing_lines: [2, 5],
                            lines: [7, 9, 8, 7, 9, 7],
                            transformed: {
                                number: 21,
                                name: 'Biting Through',
                                chinese: '噬嗑 (Shì Kè)',
                                symbol: '☲☳',
                                meaning: 'Fire over Thunder',
                                keywords: 'Piercing obstacle, enforcing justice, removing delusion',
                                upper_trigram: { symbol: '☲', name: 'Fire', element: 'Radiant Flame', nature: 'Clinging' },
                                lower_trigram: { symbol: '☳', name: 'Thunder', element: 'Awakening Shock', nature: 'Arousing' },
                                lines: [7, 8, 8, 7, 8, 7]
                            }
                        }
                    };
                    activeReadingBadge.textContent = 'I Ching reading';
                    currentTradition = currentReadingData.type;
                    renderVisualStage(currentReadingData);
                    seekerInquiryDisplay.textContent = '"What guidance does the Book of Changes hold for navigating tension?"';
                    oracleStreamText.innerHTML = '<p>The Oracle reveals <strong>Hexagram 38: Opposition (睽)</strong> transforming into <strong>Hexagram 21: Biting Through (噬嗑)</strong>...</p>';
                } else if (demoType === 'iching-steadfast') {
                    currentReadingData = {
                        type: 'iching',
                        hexagram: {
                            number: 1,
                            name: 'The Creative',
                            chinese: '乾 (Qián)',
                            symbol: '☰☰',
                            meaning: 'Heaven over Heaven',
                            keywords: 'Pure yang, primal power, perseverance, dragon in the abyss',
                            upper_trigram: { symbol: '☰', name: 'Heaven', element: 'Firmament', nature: 'Creative' },
                            lower_trigram: { symbol: '☰', name: 'Heaven', element: 'Firmament', nature: 'Creative' },
                            changing_lines: [],
                            lines: [7, 7, 7, 7, 7, 7]
                        }
                    };
                    activeReadingBadge.textContent = 'I Ching reading';
                    currentTradition = currentReadingData.type;
                    renderVisualStage(currentReadingData);
                    seekerInquiryDisplay.textContent = '"What is the ultimate creative force of my inquiry?"';
                    oracleStreamText.innerHTML = '<p>The oracle reveals <strong>Hexagram 1: The Creative (乾)</strong> in steadfast, immutable form...</p>';
                } else if (demoType === 'tarot') {
                    currentReadingData = {
                        type: 'tarot',
                        cards: [
                            { name: 'The Magician', suit: 'Major Arcana', number: 1 },
                            { name: 'The High Priestess', suit: 'Major Arcana', number: 2 },
                            { name: 'The Empress', suit: 'Major Arcana', number: 3 }
                        ],
                        positions: ['Past / Foundation', 'Present / Crossing', 'Future / Potential'],
                        spread_type: '3-card'
                    };
                    activeReadingBadge.textContent = 'Tarot reading';
                    currentTradition = currentReadingData.type;
                    renderVisualStage(currentReadingData);
                    seekerInquiryDisplay.textContent = '"What energies surround my creative endeavors?"';
                    oracleStreamText.innerHTML = '<p>The cards lay before you upon the aged walnut altar...</p>';
                } else if (demoType === 'runes') {
                    currentReadingData = {
                        type: 'runes',
                        runes: [
                            { name: 'Ansuz', rune: 'ᚨ', symbol: 'ᚨ', meaning: 'Divine Voice & Inspiration', keywords: 'Wisdom, Odin, Truth' },
                            { name: 'Raidho', rune: 'ᚱ', symbol: 'ᚱ', meaning: 'The Sacred Journey & Rhythm', keywords: 'Travel, Destiny, Alignment' },
                            { name: 'Algiz', rune: 'ᛉ', symbol: 'ᛉ', meaning: 'Sanctuary & Higher Protection', keywords: 'Shield, Elk, Divine Connection' }
                        ],
                        positions: ['Situation', 'Action', 'Outcome']
                    };
                    activeReadingBadge.textContent = 'Rune reading';
                    currentTradition = currentReadingData.type;
                    renderVisualStage(currentReadingData);
                    seekerInquiryDisplay.textContent = '"What do the ancient stones foresee on my journey?"';
                    oracleStreamText.innerHTML = '<p>The Elder Futhark runes clatter upon the sacred woven cloth...</p>';
                }
            }
        });
