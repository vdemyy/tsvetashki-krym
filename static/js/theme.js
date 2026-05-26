// Theme management with automatic sunset/sunrise switching
(function() {
  const html = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const THEME_KEY = 'theme';
  const AUTO_THEME_KEY = 'autoTheme';
  
  // Simferopol coordinates (approximate center of Crimea)
  const LATITUDE = 44.9572;
  const LONGITUDE = 34.1108;
  
  let sunTimes = null;
  let autoThemeEnabled = true;

  // Get saved theme or default to light
  function getSavedTheme() {
    return localStorage.getItem(THEME_KEY) || 'light';
  }

  // Save theme to localStorage
  function saveTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
  }

  // Check if auto theme is enabled
  function isAutoThemeEnabled() {
    const saved = localStorage.getItem(AUTO_THEME_KEY);
    return saved === null ? true : saved === 'true';
  }

  // Save auto theme preference
  function saveAutoTheme(enabled) {
    localStorage.setItem(AUTO_THEME_KEY, enabled ? 'true' : 'false');
    autoThemeEnabled = enabled;
  }

  // Apply theme
  function applyTheme(theme) {
    html.setAttribute('data-theme', theme);
    saveTheme(theme);
    updateAnimations(theme);
  }

  // Update animations based on theme
  function updateAnimations(theme) {
    console.log('Updating animations for theme:', theme);
    
    // Always stop both first
    if (window.stopPetals) {
      console.log('Stopping petals');
      window.stopPetals();
    }
    if (window.stopFireflies) {
      console.log('Stopping fireflies');
      window.stopFireflies();
    }
    
    // Then start the correct one with a small delay
    setTimeout(() => {
      if (theme === 'dark') {
        // ONLY fireflies on dark theme
        console.log('Starting fireflies for dark theme');
        if (window.startFireflies) window.startFireflies();
      } else {
        // ONLY petals on light theme
        console.log('Starting petals for light theme');
        if (window.startPetals) window.startPetals();
      }
    }, 300);
  }

  // Toggle theme manually
  function toggleTheme() {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    applyTheme(newTheme);
    
    // Disable auto theme when manually toggled
    saveAutoTheme(false);
  }

  // Fetch sun times from OpenWeather
  async function fetchSunTimes() {
    try {
      // Try to get from our backend API which has OpenWeather key
      const response = await fetch(`/api/sun-times?lat=${LATITUDE}&lon=${LONGITUDE}`);
      
      if (response.ok) {
        const data = await response.json();
        sunTimes = {
          sunrise: data.sunrise * 1000, // Convert to milliseconds
          sunset: data.sunset * 1000
        };
        return sunTimes;
      }
    } catch (error) {
      console.warn('Could not fetch sun times from API:', error);
    }
    
    // Fallback: calculate approximate times
    return calculateApproximateSunTimes();
  }

  // Calculate approximate sun times (fallback)
  function calculateApproximateSunTimes() {
    const now = new Date();
    const sunrise = new Date(now);
    const sunset = new Date(now);
    
    // Approximate times for Crimea
    sunrise.setHours(6, 0, 0, 0);
    sunset.setHours(19, 0, 0, 0);
    
    return {
      sunrise: sunrise.getTime(),
      sunset: sunset.getTime()
    };
  }

  // Determine theme based on time
  function getThemeByTime() {
    if (!sunTimes) return 'light';
    
    const now = Date.now();
    const { sunrise, sunset } = sunTimes;
    
    // Dark theme between sunset and sunrise
    if (now >= sunset || now < sunrise) {
      return 'dark';
    }
    
    return 'light';
  }

  // Apply auto theme
  function applyAutoTheme() {
    if (!autoThemeEnabled) return;
    
    const theme = getThemeByTime();
    const currentTheme = html.getAttribute('data-theme');
    
    if (theme !== currentTheme) {
      applyTheme(theme);
    }
  }

  // Update theme toggle button text with time to sunrise/sunset
  function updateThemeButtonText() {
    const textElement = document.getElementById('themeToggleText');
    if (!textElement) return;

    if (!sunTimes) {
      textElement.textContent = '';
      return;
    }

    const now = Date.now();
    const { sunrise, sunset } = sunTimes;
    let timeDiff = 0;
    let isDay = true;

    // Night condition: past sunset or before sunrise
    if (now >= sunset || now < sunrise) {
      isDay = false;
      if (now < sunrise) {
        timeDiff = sunrise - now;
      } else {
        // sunrise of next day (add 24 hours to today's sunrise)
        timeDiff = (sunrise + 24 * 60 * 60 * 1000) - now;
      }
    } else {
      isDay = true;
      timeDiff = sunset - now;
    }

    timeDiff = Math.max(0, timeDiff);

    const totalMinutes = Math.floor(timeDiff / (1000 * 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    let timeStr = '';
    if (hours > 0) {
      timeStr += `${hours}ч `;
    }
    timeStr += `${minutes}м`;

    if (isDay) {
      textElement.textContent = `До заката: ${timeStr}`;
    } else {
      textElement.textContent = `До восхода: ${timeStr}`;
    }
  }

  // Initialize theme
  async function initTheme() {
    autoThemeEnabled = isAutoThemeEnabled();
    
    // Fetch sun times
    sunTimes = await fetchSunTimes();
    
    if (autoThemeEnabled) {
      // Apply theme based on time
      applyAutoTheme();
    } else {
      // Apply saved theme
      const savedTheme = getSavedTheme();
      applyTheme(savedTheme);
    }

    // Update button text immediately
    updateThemeButtonText();
    
    // Check every minute for theme changes and update text
    setInterval(() => {
      applyAutoTheme();
      updateThemeButtonText();
    }, 60000);
  }

  // Event listeners
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

  // Initialize on load
  initTheme();
})();
