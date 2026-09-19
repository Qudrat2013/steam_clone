(function () {
    const stage = document.getElementById('iso-stage');
    const room = document.getElementById('iso-room');
    if (!stage || !room || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }

    let raf = 0;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const tick = () => {
        currentX += (targetX - currentX) * 0.08;
        currentY += (targetY - currentY) * 0.08;
        room.style.transform =
            'rotateX(' + (18 - currentY * 6) + 'deg) rotateY(' + (-22 + currentX * 8) + 'deg)';
        raf = requestAnimationFrame(tick);
    };

    stage.addEventListener('pointermove', (event) => {
        const rect = stage.getBoundingClientRect();
        targetX = ((event.clientX - rect.left) / rect.width - 0.5) * 2;
        targetY = ((event.clientY - rect.top) / rect.height - 0.5) * 2;
        if (!raf) raf = requestAnimationFrame(tick);
    });

    stage.addEventListener('pointerleave', () => {
        targetX = 0;
        targetY = 0;
    });
})();
