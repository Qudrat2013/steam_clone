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
