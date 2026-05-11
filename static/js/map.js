(() => {
  const el = document.getElementById("map");
  if (!el || typeof L === "undefined") return;

  const sidebar = document.getElementById("sidebar");
  const sidebarInner = document.getElementById("sidebar-inner");
  const closeBtn = document.getElementById("sidebar-close");

  const statusColor = {
    active: "#3d5a4a",
    soon: "#c4b8a0",
    future: "#b8bec4",
    ended: "#9aa3a8",
  };

  const statusLabel = {
    active: "идёт",
    soon: "скоро",
    future: "позже",
    ended: "завершено",
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function safeIcon(name) {
    const s = String(name || "map-pin").toLowerCase().replace(/[^a-z0-9-]/g, "");
    return s.slice(0, 48) || "map-pin";
  }

  function paintLucide() {
    if (typeof lucide !== "undefined" && lucide.createIcons) {
      lucide.createIcons({ attrs: { class: ["lucide", "lucide-icon"] } });
    }
  }

  async function openSidebar(it) {
    sidebar.classList.remove("sidebar--hidden");
    let weather = "";
    try {
      const r = await fetch(
        `/api/weather/hint?lat=${it.place.latitude}&lon=${it.place.longitude}`
      );
      const j = await r.json();
      if (j.message) weather = `<p class="weather-hint">${esc(j.message)}</p>`;
    } catch (_) {}

    const fs = it.forecast_stats;
    const fc =
      fs && (fs.start || fs.peak || fs.end)
        ? `<p class="muted">Прогноз по истории: ${esc(fs.start)} · ${esc(fs.peak)} · ${esc(
            fs.end
          )}</p>`
        : "";

    const inm = safeIcon(it.phenomenon.icon_lucide);

    sidebarInner.innerHTML = `
      <div class="side-card">
        <p class="side-card__slug"><code>${esc(it.phenomenon.slug)}</code> · #${esc(it.phenomenon.id)}</p>
        <h2 class="side-card__title side-card__title--row">
          <i data-lucide="${inm}" class="side-card__ico" aria-hidden="true"></i>
          <span>${esc(it.phenomenon.name)}</span>
        </h2>
        <p class="muted">${esc(it.place.name)} — ${esc(it.place.region || "")}${
      it.place.subregion ? " · " + esc(it.place.subregion) : ""
    }</p>
        <dl class="dates">
          <div><dt>Начало</dt><dd>${esc(it.start_date)}</dd></div>
          <div><dt>Пик</dt><dd>${esc(it.peak_date)}</dd></div>
          <div><dt>Конец</dt><dd>${esc(it.end_date)}</dd></div>
          <div><dt>Статус</dt><dd>${esc(statusLabel[it.marker_status] || it.marker_status)}</dd></div>
        </dl>
        ${fc}
        ${weather}
        <p><a class="btn" href="/p/${encodeURIComponent(it.phenomenon.slug)}">Страница явления</a></p>
      </div>
    `;
    paintLucide();
  }

  closeBtn?.addEventListener("click", () => {
    sidebar.classList.add("sidebar--hidden");
  });

  fetch("/api/events/map")
    .then((r) => r.json())
    .then((data) => {
      const map = L.map("map", { scrollWheelZoom: true }).setView([44.95, 34.11], 8);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap",
      }).addTo(map);

      const cluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 52,
        spiderfyOnMaxZoom: true,
      });

      (data.items || []).forEach((it) => {
        const col = statusColor[it.marker_status] || "#888";
        const inm = safeIcon(it.phenomenon.icon_lucide);
        const icon = L.divIcon({
          className: "mk-wrap",
          html: `<div class="mk" style="background:${col}"><i data-lucide="${inm}" class="mk-lucide" aria-hidden="true"></i></div>`,
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });
        const m = L.marker([it.place.latitude, it.place.longitude], { icon });
        m.on("click", () => openSidebar(it));
        cluster.addLayer(m);
      });

      map.addLayer(cluster);
      paintLucide();
      if (data.items && data.items.length) {
        const b = L.latLngBounds(
          data.items.map((i) => [i.place.latitude, i.place.longitude])
        );
        map.fitBounds(b.pad(0.12));
      }
    })
    .catch(() => {
      el.innerHTML = "<p class=\"empty\">Не удалось загрузить маркеры.</p>";
    });
})();
