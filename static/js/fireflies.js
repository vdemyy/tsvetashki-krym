// Fireflies animation — floating light particles
(() => {
  const COLORS = [
    "rgba(88, 166, 255, 0.6)",    // blue
    "rgba(121, 192, 255, 0.5)",   // light blue
    "rgba(210, 168, 255, 0.5)",   // purple
    "rgba(247, 120, 186, 0.4)",   // pink
    "rgba(180, 220, 255, 0.5)",   // pale blue
  ];

  let fireflyInterval = null;
  let isRunning = false;

  function createFirefly() {
    const firefly = document.createElement("div");
    firefly.className = "firefly";
    
    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    const size = 2 + Math.random() * 4; // 2-6px
    const startX = Math.random() * window.innerWidth;
    const startY = window.innerHeight + 20;
    const duration = 15 + Math.random() * 20; // 15-35s
    const delay = Math.random() * 5;
    const drift = -100 + Math.random() * 200; // horizontal drift
    
    firefly.style.cssText = `
      left: ${startX}px;
      bottom: ${-20}px;
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      animation-duration: ${duration}s;
      animation-delay: ${delay}s;
      --drift: ${drift}px;
      --glow-color: ${color};
    `;
    
    document.body.appendChild(firefly);
    
    setTimeout(() => {
      firefly.remove();
    }, (duration + delay) * 1000);
  }

  function startFireflies() {
    if (isRunning) return;
    isRunning = true;
    
    // Create initial batch
    const initialCount = 12;
    for (let i = 0; i < initialCount; i++) {
      setTimeout(() => createFirefly(), i * 800);
    }
    
    // Continue creating fireflies
    fireflyInterval = setInterval(() => {
      if (Math.random() > 0.4) { // 60% chance
        createFirefly();
      }
    }, 3000);
  }

  function stopFireflies() {
    if (!isRunning) return;
    isRunning = false;
    
    if (fireflyInterval) {
      clearInterval(fireflyInterval);
      fireflyInterval = null;
    }
    
    // Remove existing fireflies
    document.querySelectorAll('.firefly').forEach(f => f.remove());
  }

  // Export functions globally
  window.startFireflies = startFireflies;
  window.stopFireflies = stopFireflies;

  // DON'T auto-start - wait for theme.js to call us
})();
