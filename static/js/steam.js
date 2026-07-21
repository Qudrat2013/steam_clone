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

// ===== ЗАПУСК ИГРЫ ЧЕРЕЗ ЛАУНЧЕР =====

/**
 * Запускает игру через PyQt мост.
 * gamePath — путь к .exe файлу (абсолютный или относительный рядом с launcher.py)
 */
function launchGame(gamePath) {
    if (!window._pyBridge) {
        // Если открыто в обычном браузере, а не в лаунчере — скачиваем
        console.warn('[Launcher] Мост не найден — открыто в браузере, не в лаунчере.');
        return false;
    }
    window._pyBridge.launchGame(gamePath);
    return true;
}

/**
 * Останавливает запущенную игру через PyQt мост.
 */
function stopGame() {
    if (!window._pyBridge) return;
    window._pyBridge.stopGame();
}

// Вешаем обработчики на кнопки запуска игры
// Кнопка должна иметь класс btn_launch_game и атрибут data-path="путь/к/игре.exe"
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.btn_launch_game').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const path = btn.dataset.path;
            if (!path) {
                alert('Путь к игре не указан!');
                return;
            }

            const launched = launchGame(path);

            // Если мост не доступен (обычный браузер) — fallback на скачивание
            if (!launched) {
                const fallback = btn.dataset.fallback;
                if (fallback) window.location.href = fallback;
            }
        });
    });

    document.querySelectorAll('.btn_stop_game').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            stopGame();
        });
    });
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
