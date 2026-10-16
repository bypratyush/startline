"""Season planner: spot events that sit too close together.

Recovery guidance is deliberately conservative and simple: the classic "one easy
day per mile raced" for running, scaled equivalents for other sports, and a
couple of days between tournaments in court and team sports.
"""

from datetime import date

from .categories import tri_class


def recovery_days(event, cat) -> int:
    fam = event.sport.family
    d = (cat.distance_km if cat else None) or 0
    if fam == "run":
        gain = (event.course or {}).get("elevation_gain_m") or 0
        effort = d + gain / 100
        return max(3, round(effort * 0.62))
    if fam == "ride":
        return max(2, round(d / 50))
    if fam == "swim":
        return max(2, round(((cat.swim_km if cat else None) or d) * 2))
    if fam == "tri":
        return [5, 7, 14, 28, 42][tri_class(cat)] if cat else 7
    if fam == "hyrox":
        return 7
    if fam == "ocr":
        return 5
    return 2


def season_plan(entries: list[dict], today: date) -> dict:
    """entries: [{"kind": "registered"|"saved", "event": Event, "category": EventCategory|None}]"""
    upcoming = sorted(
        (e for e in entries if e["event"].end_date >= today),
        key=lambda e: e["event"].start_date,
    )
    warnings = []
    for prev, nxt in zip(upcoming, upcoming[1:], strict=False):
        gap = (nxt["event"].start_date - prev["event"].end_date).days
        need = recovery_days(prev["event"], prev["category"])
        if gap <= 0:
            warnings.append(
                {
                    "level": "clash",
                    "events": [prev["event"].slug, nxt["event"].slug],
                    "message": f"{prev['event'].name} and {nxt['event'].name} overlap.",
                }
            )
        elif gap < need:
            warnings.append(
                {
                    "level": "tight",
                    "events": [prev["event"].slug, nxt["event"].slug],
                    "message": (
                        f"Only {gap} days between {prev['event'].name} and {nxt['event'].name}. "
                        f"Recovery after {prev['category'].name if prev['category'] else 'it'} "
                        f"usually takes about {need} days."
                    ),
                }
            )
    by_month: dict[str, int] = {}
    for e in upcoming:
        key = e["event"].start_date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0) + 1
    return {"warnings": warnings, "per_month": by_month, "count": len(upcoming)}
