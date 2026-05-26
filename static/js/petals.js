// Sakura petals animation — beautiful and smooth
(() => {
  const PETAL_COLORS = [
    "#ffc0d3", // light pink
    "#ffb3c6", // pink
    "#ffd4e5", // pale pink
    "#ffe0ec", // very pale pink
    "#f8b4d9", // rose pink
  ];

  const PETAL_SVG = `
    <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2c-1.5 3-4 5-7 5 0 3.5 2.5 6.5 7 8-4.5 1.5-7 4.5-7 8 3 0 5.5-2 7-5 1.5 3 4 5 7 5 0-3.5-2.5-6.5-7-8 4.5-1.5 7-4.5 7-8-3 0-5.5 2-7 5z" opacity="0.85"/>
    </svg>
  `;

  let petalInterval = null;
  let isRunning = false;

  function createPetal() {
    const petal = document.createElement("div");
    petal.className = "petal";
    petal.innerHTML = PETAL_SVG;
    
    const color = PETAL_COLORS[Math.floor(Math.random() * PETAL_COLORS.length)];
    const size = 12 + Math.random() * 16; // 12-28px
    const startX = Math.random() * window.innerWidth;
    const duration = 8 + Math.random() * 7; // 8-15s
    const delay = Math.random() * 3; // 0-3s delay
    const swayAmount = 40 + Math.random() * 80; // horizontal sway
    const rotations = 2 + Math.random() * 3; // 2-5 full rotations
    
    petal.style.cssText = `
      left: ${startX}px;
      width: ${size}px;
      height: ${size}px;
      color: ${color};
      animation-duration: ${duration}s;
      animation-delay: ${delay}s;
      --sway: ${swayAmount}px;
      --rotations: ${rotations * 360}deg;
    `;
    
    document.body.appendChild(petal);
    
    // Remove after animation
    setTimeout(() => {
      petal.remove();
    }, (duration + delay) * 1000);
  }

  function startPetals() {
    if (isRunning) return;
    isRunning = true;
    
    // Create initial batch
    const initialCount = 8;
    for (let i = 0; i < initialCount; i++) {
      setTimeout(() => createPetal(), i * 600);
    }
    
    // Continue creating petals periodically
    petalInterval = setInterval(() => {
      if (Math.random() > 0.3) { // 70% chance
        createPetal();
      }
    }, 2500);
  }

  function stopPetals() {
    if (!isRunning) return;
    isRunning = false;
    
    if (petalInterval) {
      clearInterval(petalInterval);
      petalInterval = null;
    }
    
    // Remove existing petals
    document.querySelectorAll('.petal').forEach(p => p.remove());
  }

  // Export functions globally
  window.startPetals = startPetals;
  window.stopPetals = stopPetals;

  // DON'T auto-start - wait for theme.js to call us
})();
