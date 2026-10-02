// Flow-field particle background: particles drift along a smooth, time-varying
// vector field, leave fading trails and are pushed away by the pointer.
(() => {
  "use strict";

  const canvas = document.getElementById("bg");
  const ctx = canvas.getContext("2d");
  const toggle = document.getElementById("toggle");

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");

  const pointer = { x: -9999, y: -9999, active: false };
  let width = 0;
  let height = 0;
  let dpr = 1;
  let particles = [];
  let palette = [];
  let time = 0;
  let last = 0;
  let rafId = 0;
  // null = follow prefers-reduced-motion; "play" / "pause" = explicit user choice.
  let userChoice = null;

  function readColors() {
    const s = getComputedStyle(document.documentElement);
    palette = ["--accent-1", "--accent-2", "--accent-3"].map((v) => s.getPropertyValue(v).trim());
  }

  function particleCount() {
    // Scale with area, capped so phones stay smooth.
    const n = Math.round((width * height) / 1400);
    return Math.max(250, Math.min(n, 1400));
  }

  function spawn(p) {
    p.x = Math.random() * width;
    p.y = Math.random() * height;
    p.vx = 0;
    p.vy = 0;
    p.life = 120 + Math.random() * 280;
    p.color = palette[(Math.random() * palette.length) | 0];
    p.size = 0.6 + Math.random() * 1.4;
    return p;
  }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    clear();

    const target = particleCount();
    while (particles.length < target) particles.push(spawn({}));
    particles.length = target;
    if (!isRunning()) drawStatic();
  }

  function clear() {
    ctx.globalCompositeOperation = "source-over";
    ctx.clearRect(0, 0, width, height);
  }

  // Cheap smooth pseudo-noise from layered sines: returns an angle.
  function fieldAngle(x, y, t) {
    const s = 0.0018;
    return (
      Math.sin(x * s + t * 0.21) * 1.7 +
      Math.cos(y * s * 1.3 - t * 0.17) * 1.7 +
      Math.sin((x + y) * s * 0.6 + t * 0.11) * 1.2
    );
  }

  function step(dt) {
    time += dt * 0.6;
    const speed = 0.9;
    const radius = Math.min(180, Math.max(width, height) * 0.15);
    const r2 = radius * radius;

    // Fade previous frame toward transparent so trails dissolve.
    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    ctx.fillRect(0, 0, width, height);
    ctx.globalCompositeOperation = "source-over";

    for (const p of particles) {
      const a = fieldAngle(p.x, p.y, time);
      p.vx += Math.cos(a) * 0.12 * dt;
      p.vy += Math.sin(a) * 0.12 * dt;

      if (pointer.active) {
        const dx = p.x - pointer.x;
        const dy = p.y - pointer.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < r2 && d2 > 0.01) {
          const d = Math.sqrt(d2);
          const f = (1 - d / radius) * 1.6 * dt;
          p.vx += (dx / d) * f;
          p.vy += (dy / d) * f;
        }
      }

      p.vx *= 0.92;
      p.vy *= 0.92;

      const px = p.x;
      const py = p.y;
      p.x += p.vx * speed * dt;
      p.y += p.vy * speed * dt;
      p.life -= dt;

      ctx.strokeStyle = p.color;
      ctx.lineWidth = p.size;
      ctx.globalAlpha = Math.min(1, p.life / 60) * 0.75;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(p.x, p.y);
      ctx.stroke();

      if (p.life <= 0 || p.x < -10 || p.x > width + 10 || p.y < -10 || p.y > height + 10) {
        spawn(p);
      }
    }
    ctx.globalAlpha = 1;
  }

  // Calm, non-animated composition for reduced motion / paused state.
  function drawStatic() {
    clear();
    ctx.globalAlpha = 0.5;
    for (const p of particles) {
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function frame(now) {
    // dt normalised to 60 fps, clamped so tab switches don't cause jumps.
    const dt = last ? Math.min((now - last) / 16.667, 3) : 1;
    last = now;
    step(dt);
    rafId = requestAnimationFrame(frame);
  }

  function isRunning() {
    return rafId !== 0;
  }

  function start() {
    if (isRunning()) return;
    last = 0;
    rafId = requestAnimationFrame(frame);
  }

  function stop() {
    cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function wantsMotion() {
    return userChoice ? userChoice === "play" : !reducedMotion.matches;
  }

  function update() {
    if (wantsMotion() && !document.hidden) start();
    else {
      stop();
      if (!document.hidden) drawStatic();
    }
    const paused = !wantsMotion();
    toggle.setAttribute("aria-pressed", String(paused));
    toggle.textContent = paused ? "Animation abspielen" : "Animation pausieren";
  }

  function setPointer(e) {
    pointer.x = e.clientX;
    pointer.y = e.clientY;
    pointer.active = true;
  }

  window.addEventListener("pointermove", setPointer, { passive: true });
  window.addEventListener("pointerdown", setPointer, { passive: true });
  window.addEventListener("pointerleave", () => (pointer.active = false));
  document.addEventListener("pointerout", (e) => {
    if (!e.relatedTarget) pointer.active = false;
  });

  let resizeTimer = 0;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 120);
  });

  toggle.addEventListener("click", () => {
    userChoice = wantsMotion() ? "pause" : "play";
    update();
  });

  reducedMotion.addEventListener("change", update);
  darkScheme.addEventListener("change", () => {
    readColors();
    for (const p of particles) p.color = palette[(Math.random() * palette.length) | 0];
    clear();
    if (!isRunning()) drawStatic();
  });
  document.addEventListener("visibilitychange", update);

  readColors();
  resize();
  update();
})();
