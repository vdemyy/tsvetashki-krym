"""Иконки Lucide (kebab-case для data-lucide) по умолчанию по типу явления."""

from __future__ import annotations

from typing import Any

DEFAULT_BY_KIND: dict[str, str] = {
    "flowering": "flower-2",
    "visual": "sunrise",
    "harvest": "cherry",
    "animals": "bird",
    "activity": "calendar-days",
}


def lucide_icon_for_phenomenon(ph: Any) -> str:
    raw = getattr(ph, "icon_lucide", None) if not isinstance(ph, dict) else ph.get("icon_lucide")
    if raw and str(raw).strip():
        return str(raw).strip()
    kind = getattr(ph, "kind", None) if not isinstance(ph, dict) else ph.get("kind")
    return DEFAULT_BY_KIND.get(str(kind or ""), "sparkles")
