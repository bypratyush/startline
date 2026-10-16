"""Event guide: one page that tells an athlete everything about the day.

It merges three sources:
  * the event's own facts and tips (seeded from the organiser's published info)
  * the sport's general guide (kit, timeline, fuelling, safety, glossary)
  * the host city's climate normals for that month, turned into a start-time
    weather estimate and a heat-index band (US National Weather Service bands)
"""

from datetime import date

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# NWS heat index bands, in Celsius.
HEAT_BANDS = [
    (51.7, "extreme-danger", "Extreme danger", "Do not race hard. Organisers may shorten or cancel."),
    (
        39.4,
        "danger",
        "Danger",
        "Heat illness is likely with prolonged effort. Slow down a lot, drink to a plan, use every cooling station.",
    ),
    (
        32.2,
        "extreme-caution",
        "Extreme caution",
        "Expect to run or play slower. Pre-cool, drink with electrolytes, pour water on your head and neck.",
    ),
    (
        26.7,
        "caution",
        "Caution",
        "Fatigue comes sooner in this heat. Start conservatively and drink at every station.",
    ),
    (-99, "comfortable", "Comfortable", "Good conditions for a hard effort. Still drink to thirst."),
]


def heat_index_c(temp_c: float, rh: float) -> float:
    """Rothfusz regression (NWS) with the low-temperature simple formula."""
    t = temp_c * 9 / 5 + 32
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    if (simple + t) / 2 < 80:
        hi = simple
    else:
        hi = (
            -42.379
            + 2.04901523 * t
            + 10.14333127 * rh
            - 0.22475541 * t * rh
            - 0.00683783 * t * t
            - 0.05481717 * rh * rh
            + 0.00122874 * t * t * rh
            + 0.00085282 * t * rh * rh
            - 0.00000199 * t * t * rh * rh
        )
        if rh < 13 and 80 <= t <= 112:
            hi -= ((13 - rh) / 4) * ((17 - abs(t - 95)) / 17) ** 0.5
        elif rh > 85 and 80 <= t <= 87:
            hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return (hi - 32) * 5 / 9


def _start_fraction(start_time: str | None) -> tuple[float, str]:
    """Where between the daily low and high the temperature sits at the start."""
    if not start_time:
        return 0.5, "during the day"
    try:
        hour = int(start_time.split(":")[0])
    except ValueError:
        return 0.5, "during the day"
    if hour < 7:
        return 0.1, f"at the {start_time} start"
    if hour < 9:
        return 0.3, f"at the {start_time} start"
    if hour < 12:
        return 0.7, f"at the {start_time} start"
    if hour < 16:
        return 1.0, f"at the {start_time} start"
    if hour < 19:
        return 0.75, f"at the {start_time} start"
    return 0.45, f"at the {start_time} start"


def weather_card(city, event_date: date, start_time: str | None) -> dict | None:
    climate = city.climate or {}
    hi = climate.get("max_c")
    lo = climate.get("min_c")
    if not hi or not lo:
        return None
    m = event_date.month - 1
    rh_list = climate.get("humidity_pct") or []
    rain_list = climate.get("rain_mm") or []
    rh = rh_list[m] if len(rh_list) == 12 and rh_list[m] is not None else None
    frac, when = _start_fraction(start_time)
    temp = lo[m] + frac * (hi[m] - lo[m])
    hix = heat_index_c(temp, rh) if rh is not None else temp
    band = next(b for b in HEAT_BANDS if hix >= b[0])
    aq = city.air_quality_note if event_date.month in (10, 11, 12, 1, 2) else None
    return {
        "month": MONTHS[m],
        "max_c": hi[m],
        "min_c": lo[m],
        "humidity_pct": rh,
        "rain_mm": rain_list[m] if len(rain_list) == 12 else None,
        "start_temp_c": round(temp, 1),
        "feels_like_c": round(hix, 1),
        "when": when,
        "band": band[1],
        "band_label": band[2],
        "advice": band[3],
        "air_quality": aq,
        "source": "City climate normals (IMD), heat index bands from the US National Weather Service",
    }


def _clock(start: str, offset_min: int) -> str | None:
    try:
        h, m = (int(p) for p in start.split(":"))
    except (ValueError, AttributeError):
        return None
    total = (h * 60 + m + offset_min) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _offset_label(offset: int) -> str:
    if offset == 0:
        return "Start"
    sign = "T-" if offset < 0 else "T+"
    mins = abs(offset)
    if mins >= 1440:
        days = mins // 1440
        return f"{sign}{days} day" + ("s" if days > 1 else "")
    if mins >= 120 and mins % 60 == 0:
        return f"{sign}{mins // 60} h"
    return f"{sign}{mins} min"


def build_guide(event, category=None) -> dict:
    sport = event.sport
    sg = sport.guide or {}
    cat = (
        category
        or next((c for c in event.categories if c.start_time), None)
        or (event.categories[0] if event.categories else None)
    )
    start = cat.start_time if cat else None

    timeline = []
    for step in sg.get("timeline", []):
        off = step.get("offset_min")
        if off is None:
            timeline.append({"offset": step.get("label") or "During", "clock": None, "what": step["what"]})
            continue
        off = int(off)
        timeline.append(
            {
                "offset": _offset_label(off),
                "clock": _clock(start, off) if start and abs(off) < 1440 else None,
                "what": step["what"],
            }
        )

    course = dict(event.course or {})
    return {
        "event": event.slug,
        "category": None
        if cat is None
        else {
            "id": cat.id,
            "name": cat.name,
            "start_time": cat.start_time,
        },
        "weather": weather_card(event.city, event.start_date, start),
        "timeline": timeline,
        "kit": sg.get("kit", []),
        "nutrition": sg.get("nutrition", []),
        "safety": sg.get("safety", []),
        "beginner_tips": sg.get("beginner_tips", []),
        "training": sg.get("training", []),
        "glossary": sg.get("glossary", []),
        "event_tips": event.tips or [],
        "amenities": event.amenities or [],
        "course": course,
        "format": event.format,
        "venue": {
            "name": event.venue,
            "lat": event.lat,
            "lon": event.lon,
            "maps_url": f"https://www.google.com/maps/search/?api=1&query={event.lat},{event.lon}",
            "city": event.city.name,
            "city_note": event.city.sports_note,
        },
        "official_url": event.official_url,
        "registration": {
            "status": event.registration_status,
            "opens": event.registration_opens.isoformat() if event.registration_opens else None,
            "closes": event.registration_closes.isoformat() if event.registration_closes else None,
            "url": event.registration_url,
            "notes": event.registration_notes,
        },
        "sources": event.sources or [],
    }
