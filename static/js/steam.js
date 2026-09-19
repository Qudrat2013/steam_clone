// ===== STEAM CLONE JS =====

// Auto-close messages
document.querySelectorAll('.close_alert').forEach(btn => {
    btn.addEventListener('click', () => btn.parentElement.remove());
});
setTimeout(() => {
    document.querySelectorAll('.alert').forEach(el => el.remove());
}, 5000);

// ===== CAROUSEL =====
const slides = document.querySelectorAll('.carousel_slide');
const dots = document.querySelectorAll('.carousel_dot');
let current = 0, timer;

function showSlide(n) {
    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));
    current = (n + slides.length) % slides.length;
    if (slides[current]) slides[current].classList.add('active');
    if (dots[current]) dots[current].classList.add('active');
}

function startTimer() {
    clearInterval(timer);
    timer = setInterval(() => showSlide(current + 1), 5000);
}

if (slides.length > 0) {
    showSlide(0);
    startTimer();
    document.querySelector('.carousel_prev')?.addEventListener('click', () => { showSlide(current - 1); startTimer(); });
    document.querySelector('.carousel_next')?.addEventListener('click', () => { showSlide(current + 1); startTimer(); });
    dots.forEach((dot, i) => dot.addEventListener('click', () => { showSlide(i); startTimer(); }));
}

// ===== SCREENSHOT GALLERY =====
const mainShot = document.querySelector('.main_screenshot');
document.querySelectorAll('.screenshot_thumb').forEach(thumb => {
    thumb.addEventListener('click', () => {
        if (mainShot) mainShot.src = thumb.src;
        document.querySelectorAll('.screenshot_thumb').forEach(t => t.classList.remove('active'));
        thumb.classList.add('active');
    });
});

// ===== ЗАПУСК ИГРЫ + РЕАЛЬНОЕ ВРЕМЯ СЕССИИ =====

function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const match = document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('csrftoken='));
    return match ? decodeURIComponent(match.split('=').slice(1).join('=')) : '';
}

function formatPlayDuration(seconds) {
    seconds = Math.max(0, Math.floor(Number(seconds) || 0));
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h) return `${h} ч. ${m} мин.`;
    if (m) return s ? `${m} мин. ${s} сек.` : `${m} мин.`;
    return s ? `${s} сек.` : '0 мин.';
}

function launchGame(gamePath, gameId) {
    if (!window._pyBridge) return false;
    try {
        window._pyBridge.launchGame(gamePath, Number(gameId) || 0);
        return true;
    } catch (err) {
        console.warn('[Launcher] launchGame failed', err);
        return false;
    }
}

function stopGame() {
    if (!window._pyBridge) return;
    try { window._pyBridge.stopGame(); } catch (e) { /* ignore */ }
}

const SteamPlay = {
    session: null,
    timer: null,
    heartbeat: null,
    tickStarted: 0,

    async post(url, body) {
        const res = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(body || {}),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw data;
        return data;
    },

    async start(gameId, opts) {
        opts = opts || {};
        gameId = Number(gameId);
        if (!gameId) return;

        if (this.session && this.session.game_id !== gameId) {
            await this.end();
        }

        const inLauncher = Boolean(window.STEAM_LAUNCHER && window._pyBridge);
        const path = opts.path || '';

        if (inLauncher && path) {
            launchGame(path, gameId);
        }

        const data = await this.post(`/plus/play/${gameId}/start/`, {
            source: inLauncher ? 'launcher' : 'web',
        });
        this.apply(data, true);
        if (!inLauncher) {
            this.hint('Время считается, пока открыта сессия. .exe запускается через Steam Clone Launcher.');
        }
    },

    async beat() {
        if (!this.session) return;
        try {
            const data = await this.post(`/plus/play/${this.session.game_id}/heartbeat/`, {
                session_id: this.session.session_id,
            });
            this.apply(data, false);
        } catch (e) {
            /* session may have expired */
        }
    },

    async end() {
        if (!this.session) {
            this.hide();
            return;
        }
        const gameId = this.session.game_id;
        const sessionId = this.session.session_id;
        try {
            stopGame();
        } catch (e) { /* ignore */ }
        try {
            const data = await this.post(`/plus/play/${gameId}/end/`, { session_id: sessionId });
            this.updatePlaytime(gameId, data.total_display, data.sessions);
        } catch (e) { /* ignore */ }
        this.session = null;
        this.hide();
    },

    onLaunched(gameId) {
        /* Python confirms process started */
        if (this.session && Number(this.session.game_id) === Number(gameId)) return;
        this.start(gameId, {});
    },

    onExited(gameId, seconds) {
        if (this.session && Number(this.session.game_id) === Number(gameId)) {
            this.end();
        }
    },

    apply(data, restartTimer) {
        if (!data || !data.playing) {
            this.session = null;
            this.hide();
            return;
        }
        this.session = data;
        this.tickStarted = Date.now() - (Number(data.elapsed_seconds) || 0) * 1000;
        this.show();
        this.updateButtons();
        this.updatePlaytime(data.game_id, data.total_display, data.sessions);
        if (restartTimer || !this.timer) this.startTimers();
    },

    startTimers() {
        this.stopTimers();
        this.timer = setInterval(() => this.tick(), 1000);
        this.heartbeat = setInterval(() => this.beat(), 20000);
        this.tick();
    },

    stopTimers() {
        if (this.timer) clearInterval(this.timer);
        if (this.heartbeat) clearInterval(this.heartbeat);
        this.timer = null;
        this.heartbeat = null;
    },

    tick() {
        if (!this.session) return;
        const elapsed = Math.max(0, Math.floor((Date.now() - this.tickStarted) / 1000));
        const el = document.getElementById('np-time');
        if (el) el.textContent = formatPlayDuration(elapsed);
        document.querySelectorAll(`.js-session-time-${this.session.game_id}`).forEach(node => {
            node.textContent = formatPlayDuration(elapsed);
        });
    },

    show() {
        const bar = document.getElementById('steam-now-playing');
        const title = document.getElementById('np-game-title');
        if (title && this.session) title.textContent = this.session.game_title || '';
        if (bar) {
            bar.hidden = false;
            document.body.classList.add('has-now-playing');
        }
        this.updateButtons();
    },

    hide() {
        this.stopTimers();
        const bar = document.getElementById('steam-now-playing');
        if (bar) bar.hidden = true;
        document.body.classList.remove('has-now-playing');
        this.updateButtons();
    },

    updateButtons() {
        const playingId = this.session ? String(this.session.game_id) : '';
        document.querySelectorAll('.js-play-btn, .btn_launch_game').forEach(btn => {
            const id = String(btn.dataset.gameId || '');
            if (!id) return;
            btn.hidden = Boolean(playingId && id === playingId);
        });
        document.querySelectorAll('.js-stop-btn, .btn_stop_game').forEach(btn => {
            const id = String(btn.dataset.gameId || '');
            if (!id) {
                btn.hidden = !playingId;
                return;
            }
            btn.hidden = id !== playingId;
        });
        document.querySelectorAll('.steam_library_game_link').forEach(link => {
            link.classList.toggle('is-playing', String(link.dataset.gameId) === playingId);
        });
    },

    updatePlaytime(gameId, display) {
        if (!display) return;
        document.querySelectorAll(`.js-playtime-${gameId}`).forEach(node => {
            node.textContent = display;
        });
    },

    hint(text) {
        if (!text) return;
        const bar = document.getElementById('steam-now-playing');
        if (!bar) return;
        let hint = bar.querySelector('.np-hint');
        if (!hint) {
            hint = document.createElement('div');
            hint.className = 'np-hint';
            bar.appendChild(hint);
        }
        hint.textContent = text;
    },

    async restore() {
        if (!window.STEAM_PLAY_STATUS) return;
        try {
            const res = await fetch(window.STEAM_PLAY_STATUS, {
                headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            });
            const data = await res.json();
            if (data && data.playing) this.apply(data, true);
        } catch (e) { /* ignore */ }
    },
};

window.SteamPlay = SteamPlay;

function launchGameFromButton(btn) {
    const gameId = btn.dataset.gameId;
    SteamPlay.start(gameId, { path: btn.dataset.path || '' });
}

document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('click', (e) => {
        const playBtn = e.target.closest('.js-play-btn, .btn_launch_game');
        if (playBtn) {
            e.preventDefault();
            launchGameFromButton(playBtn);
            return;
        }
        const stopBtn = e.target.closest('.js-stop-btn, .btn_stop_game, #steam-stop-play');
        if (stopBtn) {
            e.preventDefault();
            SteamPlay.end();
        }
    });

    SteamPlay.restore();

    window.addEventListener('beforeunload', () => {
        if (!SteamPlay.session) return;
        const gameId = SteamPlay.session.game_id;
        const sessionId = SteamPlay.session.session_id;
        const fd = new FormData();
        fd.append('csrfmiddlewaretoken', csrfToken());
        fd.append('session_id', sessionId);
        navigator.sendBeacon?.(`/plus/play/${gameId}/end/`, fd);
    });

    const search = document.getElementById('library-search');
    if (search) {
        search.addEventListener('input', () => {
            const q = search.value.trim().toLowerCase();
            document.querySelectorAll('.steam_library_game_link').forEach(link => {
                const title = (link.dataset.title || link.textContent || '').toLowerCase();
                link.hidden = q && !title.includes(q);
            });
        });
    }

    document.querySelectorAll('.steam_library_game_link').forEach(link => {
        link.addEventListener('click', (e) => {
            const id = link.dataset.gameId;
            const panel = document.getElementById(`game-${id}`);
            if (!panel) return;
            e.preventDefault();
            document.querySelectorAll('.steam_library_game_link').forEach(l => l.classList.remove('is-active'));
            document.querySelectorAll('.steam_library_game_panel').forEach(p => p.classList.remove('is-visible'));
            link.classList.add('is-active');
            panel.classList.add('is-visible');
            history.replaceState(null, '', `#game-${id}`);
        });
    });

    if (location.hash.startsWith('#game-')) {
        const link = document.querySelector(`.steam_library_game_link[href="${location.hash}"]`);
        if (link) link.click();
    }
});
// ===== LIVE SEARCH SUGGEST =====
(function () {
    const input = document.getElementById('steam-search-input');
    const box = document.getElementById('steam-search-suggest');
    if (!input || !box) return;

    let timer = null;
    let lastQ = '';

    function hide() {
        box.hidden = true;
        box.innerHTML = '';
    }

    function render(results) {
        if (!results.length) {
            hide();
            return;
        }
        box.innerHTML = results.map(r => {
            const disc = r.discount ? `<span style="color:#beee11">-${r.discount}%</span> ` : '';
            const img = r.image ? `<img src="${r.image}" alt="">` : '<div style="width:72px;height:34px;background:#111;border-radius:4px"></div>';
            return `<a href="${r.url}">${img}<div><div class="ss-title">${r.title}</div><div class="ss-meta">${r.developer || ''} · ${disc}${r.price} UZS</div></div></a>`;
        }).join('');
        box.hidden = false;
    }

    input.addEventListener('input', () => {
        const q = input.value.trim();
        clearTimeout(timer);
        if (q.length < 2) {
            hide();
            return;
        }
        timer = setTimeout(async () => {
            if (q === lastQ) return;
            lastQ = q;
            try {
                const res = await fetch(`/plus/search/suggest/?q=${encodeURIComponent(q)}`);
                const data = await res.json();
                render(data.results || []);
            } catch (e) {
                hide();
            }
        }, 220);
    });

    input.addEventListener('blur', () => setTimeout(hide, 180));
    document.addEventListener('click', (e) => {
        if (!box.contains(e.target) && e.target !== input) hide();
    });
})();
