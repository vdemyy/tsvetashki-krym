(() => {
  function run() {
    if (typeof lucide === "undefined" || !lucide.createIcons) return;
    lucide.createIcons({
      attrs: { class: ["lucide", "lucide-icon"] },
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
