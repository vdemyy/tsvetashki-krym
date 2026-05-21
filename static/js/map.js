(() => {
  const el = document.getElementById("map");
  if (!el || typeof L === "undefined") return;

  const sidebar = document.getElementById("sidebar");
  const sidebarInner = document.getElementById("sidebar-inner");
  const closeBtn = document.getElementById("sidebar-close");

  const statusColor = {
    active: "#2f6b47",
    soon: "#b07d3a",
    future: "#5a7a8a",
    ended: "#8a9090",
  };

  const statusLabel = {
    active: "идёт",
    soon: "скоро",
    future: "позже",
    ended: "завершено",
  };

  // Inline SVG paths for common Lucide icons — avoids DOM re-init on every marker
  const SVG_ICONS = {
    "flower-2": '<path d="M12 5a3 3 0 1 1 3 3m-3-3a3 3 0 1 0-3 3m3-3v1M9 8a3 3 0 1 0 3 3M9 8h1m5 0a3 3 0 1 1-3 3m3-3h-1m-2 3v-1m-3.5-1.5L7 9m1.5 1.5L7 12m4.5-1.5L13 9m-1.5 1.5L13 12M12 12v7"/><circle cx="12" cy="12" r="3"/>',
    "sunrise": '<path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/><path d="M2 18h2"/><path d="M20 18h2"/><path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/><path d="m8 6 4-4 4 4"/><path d="M16 18a4 4 0 0 0-8 0"/>',
    "cherry": '<path d="M2 17a5 5 0 0 0 10 0c0-2.76-2.5-5-5-3-2.5-2-5 .24-5 3z"/><path d="M12 17a5 5 0 0 0 10 0c0-2.76-2.5-5-5-3-2.5-2-5 .24-5 3z"/><path d="M7 14c3.22-2.91 4.29-8.75 5-12 1.66 2.38 4.94 9 5 12"/><path d="M22 9c-4.29 0-7.14-2.33-10-7 5.71 0 10 4.67 10 7z"/>',
    "bird": '<path d="M16 7h.01"/><path d="M3.4 18H12a8 8 0 0 0 8-8V7a4 4 0 0 0-7.28-2.3L2 20"/><path d="m20 7 2 .5-2 .5"/><path d="M10 18v3"/><path d="M14 17.75v3.25"/><path d="M7 18a6 6 0 0 0 3.84-10.61"/>',
    "calendar-days": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="M8 14h.01"/><path d="M12 14h.01"/><path d="M16 14h.01"/><path d="M8 18h.01"/><path d="M12 18h.01"/><path d="M16 18h.01"/>',
    "map-pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    "sparkles": '<path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    "tree-pine": '<path d="m17 14 3 3.3a1 1 0 0 1-.7 1.7H4.7a1 1 0 0 1-.7-1.7L7 14"/><path d="m14 10 3 3.3a1 1 0 0 1-.7 1.7H7.7a1 1 0 0 1-.7-1.7L10 10"/><path d="M12 2 8 7h8z"/><path d="M12 22v-3"/>',
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
  };

  function getSvgPath(iconName) {
    const name = String(iconName || "map-pin").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 48) || "map-pin";
    return SVG_ICONS[name] || SVG_ICONS["map-pin"];
  }

  function makeSvg(iconName, cls, size) {
    const path = getSvgPath(iconName);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="${cls}" aria-hidden="true">${path}</svg>`;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatWindDir(deg) {
    if (deg == null) return "";
    const dirs = ["С","СВ","В","ЮВ","Ю","ЮЗ","З","СЗ"];
    return dirs[Math.round(deg / 45) % 8];
  }

  async function openSidebar(it) {
    sidebar.classList.remove("sidebar--hidden");
    
    // Hide clouds layer when sidebar opens
    const checkbox = document.getElementById("clouds-toggle");
    if (cloudsVisible && cloudsLayer && checkbox) {
      mapInstance.removeLayer(cloudsLayer);
      cloudsLayer = null;
      cloudsVisible = false;
      checkbox.checked = false;
    }
    
    const statusBadge = `<span class="badge badge--${esc(it.marker_status)}">${esc(statusLabel[it.marker_status] || it.marker_status)}</span>`;
    const iconSvg = makeSvg(it.phenomenon.icon_lucide, "side-card__ico", 22);
    
    const fs = it.forecast_stats;
    const fc = fs && (fs.start || fs.peak || fs.end)
      ? `<div class="forecast-row"><span class="forecast-label">Прогноз:</span> ${esc(fs.start || "?")} → ${esc(fs.peak || "?")} → ${esc(fs.end || "?")}</div>`
      : "";

    // Render immediately without weather
    sidebarInner.innerHTML = `
      <div class="side-card">
        <div class="side-card__header">
          <div class="side-card__iconbox">${iconSvg}</div>
          <div class="side-card__meta">
            <p class="side-card__slug"><code>${esc(it.phenomenon.slug)}</code></p>
            ${statusBadge}
          </div>
        </div>
        <h2 class="side-card__title">${esc(it.phenomenon.name)}</h2>
        <p class="side-card__place">${makeSvg("map-pin","side-card__place-ico",14)} ${esc(it.place.name)}${it.place.region ? " · " + esc(it.place.region) : ""}${it.place.subregion ? " · " + esc(it.place.subregion) : ""}</p>
        <dl class="dates">
          <div><dt>Начало</dt><dd>${esc(it.start_date)}</dd></div>
          <div><dt>Пик</dt><dd>${esc(it.peak_date)}</dd></div>
          <div><dt>Конец</dt><dd>${esc(it.end_date)}</dd></div>
          <div><dt>Сила</dt><dd>${esc(it.intensity)}/5</dd></div>
        </dl>
        ${fc}
        <div id="weather-placeholder" class="weather-loading">Загрузка погоды...</div>
        <a class="btn btn--full" href="/p/${encodeURIComponent(it.phenomenon.slug)}">Подробнее →</a>
      </div>
    `;

    // Load weather async
    try {
      const r = await fetch(`/api/weather/hint?lat=${it.place.latitude}&lon=${it.place.longitude}`);
      const j = await r.json();
      const wd = j.weather_details;
      let weatherHtml = "";
      
      if (wd) {
        const parts = [];
        if (wd.temp_c != null) parts.push(`<span class="wt-item"><span class="wt-ico">🌡</span>${Math.round(wd.temp_c)}°C</span>`);
        if (wd.feels_like_c != null && Math.abs(wd.feels_like_c - wd.temp_c) > 1)
          parts.push(`<span class="wt-item"><span class="wt-ico">🤔</span>ощущ. ${Math.round(wd.feels_like_c)}°C</span>`);
        if (wd.humidity != null) parts.push(`<span class="wt-item"><span class="wt-ico">💧</span>${wd.humidity}%</span>`);
        if (wd.wind_speed_ms != null) parts.push(`<span class="wt-item"><span class="wt-ico">💨</span>${wd.wind_speed_ms.toFixed(1)} м/с</span>`);
        if (wd.weather_desc_ru) parts.push(`<span class="wt-item wt-item--desc">${esc(wd.weather_desc_ru)}</span>`);
        if (parts.length) {
          weatherHtml = `<div class="weather-widget">${parts.join("")}</div>`;
        }
      }
      if (j.message && !weatherHtml) {
        weatherHtml = `<p class="weather-hint">${esc(j.message)}</p>`;
      }
      
      const placeholder = document.getElementById("weather-placeholder");
      if (placeholder) {
        placeholder.outerHTML = weatherHtml || "";
      }
    } catch (_) {
      const placeholder = document.getElementById("weather-placeholder");
      if (placeholder) placeholder.remove();
    }
  }

  function createMarkerIcon(it) {
    const col = statusColor[it.marker_status] || "#888";
    const iconSvg = makeSvg(it.phenomenon.icon_lucide, "mk-svg", 18);
    return L.divIcon({
      className: "mk-wrap",
      html: `<div class="mk" style="background:${col}" title="${esc(it.phenomenon.name)}">${iconSvg}</div>`,
      iconSize: [38, 38],
      iconAnchor: [19, 19],
    });
  }

  closeBtn?.addEventListener("click", () => {
    sidebar.classList.add("sidebar--hidden");
  });

  // Close sidebar on ESC key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !sidebar.classList.contains("sidebar--hidden")) {
      sidebar.classList.add("sidebar--hidden");
    }
  });

  // Close sidebar on click outside (on map)
  el.addEventListener("click", (e) => {
    if (!sidebar.classList.contains("sidebar--hidden") && 
        !sidebar.contains(e.target) && 
        !e.target.closest(".mk")) {
      sidebar.classList.add("sidebar--hidden");
    }
  });

  // Weather layer toggle — only clouds (most useful and visible)
  let cloudsLayer = null;
  let cloudsVisible = false;
  let mapInstance = null;

  function toggleCloudsLayer() {
    if (!mapInstance) return;
    const checkbox = document.getElementById("clouds-toggle");
    const isChecked = checkbox?.checked;
    
    if (!isChecked && cloudsLayer) {
      mapInstance.removeLayer(cloudsLayer);
      cloudsLayer = null;
      cloudsVisible = false;
    } else if (isChecked && !cloudsLayer) {
      cloudsLayer = L.tileLayer(
        `https://tile.openweathermap.org/map/clouds_new/{z}/{x}/{y}.png?appid=4181eed8c54493ee89dc4f3443aae9b4`,
        { opacity: 0.5, attribution: "© OpenWeatherMap" }
      );
      cloudsLayer.addTo(mapInstance);
      cloudsVisible = true;
    }
  }

  fetch("/api/events/map")
    .then((r) => r.json())
    .then((data) => {
      const map = L.map("map", {
        scrollWheelZoom: true,
        zoomControl: true,
      }).setView([44.95, 34.11], 8);

      mapInstance = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(map);

      // Custom cluster group — no Lucide re-init needed, pure SVG
      const cluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 60,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 15,
        animate: true,
        animateAddingMarkers: false,
        chunkedLoading: true,
        chunkInterval: 100,
        chunkDelay: 50,
        iconCreateFunction: function(c) {
          const count = c.getChildCount();
          const size = count < 10 ? 36 : count < 50 ? 42 : 48;
          return L.divIcon({
            html: `<div class="cluster-mk" style="width:${size}px;height:${size}px"><span>${count}</span></div>`,
            className: "cluster-wrap",
            iconSize: [size, size],
            iconAnchor: [size/2, size/2],
          });
        },
      });

      const markers = [];
      (data.items || []).forEach((it) => {
        if (!it.place.latitude || !it.place.longitude) return;
        const icon = createMarkerIcon(it);
        const m = L.marker([it.place.latitude, it.place.longitude], { icon });
        m.on("click", () => openSidebar(it));
        markers.push(m);
      });

      cluster.addLayers(markers);
      map.addLayer(cluster);

      if (data.items && data.items.length) {
        const valid = data.items.filter(i => i.place.latitude && i.place.longitude);
        if (valid.length) {
          const b = L.latLngBounds(valid.map((i) => [i.place.latitude, i.place.longitude]));
          map.fitBounds(b.pad(0.1));
        }
      }

      // Weather controls
      const cloudsCtrl = document.getElementById("clouds-toggle");
      cloudsCtrl?.addEventListener("change", toggleCloudsLayer);
    })
    .catch(() => {
      el.innerHTML = '<p class="empty" style="padding:2rem;text-align:center">Не удалось загрузить маркеры.</p>';
    });
})();
