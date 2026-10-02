// Eine Katze, die unten über die Seite läuft: Sie sucht sich ein Ziel auf dem
// "Boden", läuft hin, bleibt eine Weile stehen und zieht dann weiter.
// Sie hält still, wenn die Animation pausiert ist (siehe main.js).
(() => {
  "use strict";

  const cat = document.getElementById("cat");
  const toggle = document.getElementById("toggle");

  const SPEED = 70; // Pixel pro Sekunde

  let x = 0;
  let y = 0;
  let target = null;
  let restUntil = 0;
  let last = 0;
  let rafId = 0;

  function size() {
    return { w: cat.offsetWidth, h: cat.offsetHeight };
  }

  // Der "Boden": das untere Fünftel des Fensters.
  function randomSpot() {
    const { w, h } = size();
    const maxY = Math.max(0, window.innerHeight - h - 8);
    const minY = Math.min(window.innerHeight * 0.8, maxY);
    return {
      x: Math.random() * Math.max(0, window.innerWidth - w),
      y: minY + Math.random() * (maxY - minY),
    };
  }

  function place() {
    cat.style.transform = `translate(${x}px, ${y}px)`;
  }

  function isPaused() {
    return toggle.getAttribute("aria-pressed") === "true";
  }

  function frame(now) {
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;

    if (!target) {
      if (now >= restUntil) {
        target = randomSpot();
        cat.classList.toggle("is-left", target.x < x);
        cat.classList.add("is-walking");
      }
    } else {
      const dx = target.x - x;
      const dy = target.y - y;
      const dist = Math.hypot(dx, dy);
      const stepLen = SPEED * dt;
      if (dist <= stepLen) {
        x = target.x;
        y = target.y;
        target = null;
        restUntil = now + 1500 + Math.random() * 3500;
        cat.classList.remove("is-walking");
      } else {
        x += (dx / dist) * stepLen;
        y += (dy / dist) * stepLen;
      }
      place();
    }

    rafId = requestAnimationFrame(frame);
  }

  function update() {
    const paused = isPaused();
    cat.classList.toggle("is-still", paused);
    if (paused) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    } else if (!rafId) {
      last = performance.now();
      rafId = requestAnimationFrame(frame);
    }
  }

  // Nach Größenänderung die Katze zurück auf den Boden holen.
  window.addEventListener("resize", () => {
    const spot = randomSpot();
    const { w } = size();
    x = Math.min(x, Math.max(0, window.innerWidth - w));
    y = spot.y;
    target = null;
    place();
  });

  const start = randomSpot();
  x = start.x;
  y = start.y;
  place();

  new MutationObserver(update).observe(toggle, { attributes: true, attributeFilter: ["aria-pressed"] });
  update();
})();
