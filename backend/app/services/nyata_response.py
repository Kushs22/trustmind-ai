"""Format Nyata live listings into UI-ready local support cards."""

from __future__ import annotations

from typing import Any


def _badge_list(item: dict[str, Any]) -> list[str]:
    badges: list[str] = []
    verification = str(item.get("verification") or "").strip().lower()
    if verification == "verified":
        badges.append("Verified")
    if item.get("open_now") is True:
        badges.append("Open now")
    if item.get("booking_required") is True:
        badges.append("Booking needed")
    service_type = str(item.get("service_type") or item.get("type") or "").strip()
    if service_type:
        badges.append(service_type.replace("_", " ").title())
    return badges


def _format_when(item: dict[str, Any]) -> str:
    day = str(item.get("day") or "").strip()
    start = str(item.get("start_time") or "").strip()
    end = str(item.get("end_time") or "").strip()
    next_date = str(item.get("next_date") or "").strip()
    parts: list[str] = []
    if day:
        parts.append(day)
    if start and end:
        parts.append(f"{start}–{end}")
    elif start:
        parts.append(start)
    if next_date:
        parts.append(next_date)
    return " · ".join(parts)


def _sort_listings(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple[int, float, str]:
        open_now = 0 if item.get("open_now") is True else 1
        try:
            distance = float(item.get("distance_km") if item.get("distance_km") is not None else 9_999)
        except (TypeError, ValueError):
            distance = 9_999.0
        name = str(item.get("name") or "")
        return (open_now, distance, name)

    return sorted(results, key=key)


def build_local_support_card(nyata_result: dict[str, Any] | None) -> dict[str, Any] | None:
    """Turn a Nyata client payload into a frontend card. None if nothing to show."""
    data = nyata_result or {}
    if not data.get("ok"):
        return None
    raw_results = [r for r in (data.get("results") or []) if isinstance(r, dict)]
    reply = str(data.get("reply") or "").strip()
    if not raw_results and not reply:
        return None

    listings: list[dict[str, Any]] = []
    for item in _sort_listings(raw_results)[:6]:
        distance = item.get("distance_km")
        try:
            distance_km = float(distance) if distance is not None else None
        except (TypeError, ValueError):
            distance_km = None
        listings.append(
            {
                "type": str(item.get("type") or "charity_service"),
                "name": str(item.get("name") or "Local service"),
                "organisation": str(item.get("organisation") or ""),
                "verification": str(item.get("verification") or ""),
                "verified": str(item.get("verification") or "").lower() == "verified",
                "service_type": str(item.get("service_type") or ""),
                "open_now": bool(item.get("open_now")),
                "booking_required": bool(item.get("booking_required")),
                "booking_warning": (
                    "You may need to book ahead — TrustMind cannot make bookings."
                    if item.get("booking_required")
                    else ""
                ),
                "address": str(item.get("address") or ""),
                "postcode": str(item.get("postcode") or ""),
                "distance_km": distance_km,
                "directions_url": str(item.get("directions_url") or ""),
                "when": _format_when(item),
                "badges": _badge_list(item),
            }
        )

    return {
        "provider": "Nyata AI",
        "city": "Bristol",
        "category": str(data.get("category") or ""),
        "summary": reply,
        "listings": listings,
        "quota_remaining": data.get("quota_remaining"),
        "disclaimer": (
            "Local listings are provided by Nyata AI from verified Bristol organisations. "
            "Times can change — check with the provider before you travel."
        ),
    }
