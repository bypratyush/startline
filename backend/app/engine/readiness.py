"""Readiness calculator: "am I ready for this category on this date?"

One assessor per sport family. Each returns the same shape:

    score       0-100, a weighted sum of components
    verdict     ready (80+) | nearly (60-79) | build (40-59) | not-this-one (<40)
    prediction  estimated finish (endurance only), splits, cutoff margin
    components  the weighted parts of the score, each with a one-line explanation
    gaps        concrete actions, most important first
    plan        week-by-week runway from today to the event

The constants and the evidence behind them are documented in
backend/app/engine/README.md. Predictions are estimates, and the UI says so.
"""

import math
from datetime import date, timedelta

from .categories import format_seconds, level_index, parse_duration, rating_bracket, tri_class

VERDICTS = [
    (80, "ready", "Race ready"),
    (60, "nearly", "Nearly there"),
    (40, "build", "Build first"),
    (0, "not-this-one", "Not this one yet"),
]

LEVEL_CHOICES = [
    {"value": "beginner", "label": "Beginner"},
    {"value": "intermediate", "label": "Intermediate"},
    {"value": "advanced", "label": "Advanced"},
]


class ReadinessError(ValueError):
    pass


# --------------------------------------------------------------------------
# form definitions
# --------------------------------------------------------------------------


def _num(id_, label, unit, lo, hi, step=1, help_=None, default=None):
    return {
        "id": id_,
        "label": label,
        "type": "number",
        "unit": unit,
        "min": lo,
        "max": hi,
        "step": step,
        "help": help_,
        "default": default,
    }


def _dur(id_, label, help_=None, default=None, fmt="mm:ss"):
    return {"id": id_, "label": label, "type": "duration", "format": fmt, "help": help_, "default": default}


def _choice(id_, label, options, help_=None, default=None):
    return {"id": id_, "label": label, "type": "choice", "options": options, "help": help_, "default": default}


RECENT_RACE = [
    {"value": "5", "label": "5K"},
    {"value": "10", "label": "10K"},
    {"value": "21.1", "label": "Half marathon"},
    {"value": "42.2", "label": "Marathon"},
]

FORMS = {
    "run": [
        _choice("recent_distance", "A recent race or time trial", RECENT_RACE, "Your most recent all-out effort", "5"),
        _dur("recent_time", "Your time for it", "h:mm:ss or mm:ss", "30:00", "h:mm:ss"),
        _num("longest_run_km", "Longest run in the last 4 weeks", "km", 0, 120, 0.5, default=8),
        _num("weekly_km", "Average weekly distance", "km", 0, 250, 1, "Last 4 weeks", 20),
        _num("runs_per_week", "Runs per week", "runs", 1, 14, 1, default=3),
    ],
    "trail": [
        _choice("recent_distance", "A recent road race or time trial", RECENT_RACE, None, "10"),
        _dur("recent_time", "Your time for it", "h:mm:ss or mm:ss", "60:00", "h:mm:ss"),
        _num("longest_run_km", "Longest run in the last 4 weeks", "km", 0, 150, 0.5, default=12),
        _num("weekly_km", "Average weekly distance", "km", 0, 250, 1, "Last 4 weeks", 25),
        _num("climb_m", "Most climbing in a single run", "m", 0, 5000, 50, "Elevation gain", 300),
    ],
    "ride": [
        _num("longest_ride_km", "Longest ride in the last 6 weeks", "km", 0, 1200, 5, default=50),
        _num("avg_speed_kmh", "Average speed on a solo ride", "km/h", 8, 45, 0.5, "Moving average", 22),
        _num("weekly_km", "Average weekly distance", "km", 0, 1500, 10, "Last 4 weeks", 100),
        _num("climb_m", "Most climbing in a single ride", "m", 0, 6000, 50, default=300),
    ],
    "swim": [
        _dur("pace_100m", "Pace per 100 m", "Steady freestyle in a pool, mm:ss", "2:30"),
        _num("longest_swim_m", "Longest non-stop swim", "m", 0, 20000, 50, "In the last 4 weeks", 800),
        _num("open_water_swims", "Open-water swims in the last 3 months", "swims", 0, 60, 1, None, 0),
        _num("sessions_per_week", "Swim sessions per week", "sessions", 0, 14, 1, default=2),
    ],
    "tri": [
        _dur("swim_pace_100m", "Swim pace per 100 m", "mm:ss", "2:30"),
        _num("longest_swim_m", "Longest non-stop swim", "m", 0, 10000, 50, None, 750),
        _num("bike_speed_kmh", "Average bike speed", "km/h", 10, 45, 0.5, None, 24),
        _num("longest_ride_km", "Longest ride in the last 6 weeks", "km", 0, 400, 5, None, 40),
        _dur("run_10k_time", "10K run time", "h:mm:ss or mm:ss", "60:00", "h:mm:ss"),
        _num("longest_run_km", "Longest run in the last 4 weeks", "km", 0, 60, 0.5, None, 8),
        _num("open_water_swims", "Open-water swims in the last 3 months", "swims", 0, 60, 1, None, 0),
    ],
    "hyrox": [
        _dur("run_5k_time", "5K run time", "mm:ss", "28:00"),
        _choice(
            "stations",
            "The 8 workout stations",
            [
                {"value": "new", "label": "New to sleds and wall balls"},
                {"value": "some", "label": "Can do them all, slowly"},
                {"value": "strong", "label": "Comfortable with all eight"},
            ],
            "SkiErg, sled push and pull, burpee broad jumps, row, farmers carry, lunges, wall balls",
            "some",
        ),
        _num("sessions_per_week", "Training sessions per week", "sessions", 0, 14, 1, None, 3),
        _num("wall_balls", "Wall balls unbroken", "reps", 0, 150, 5, "Open division ball: 6 kg women, 9 kg men", 20),
    ],
    "ocr": [
        _dur("run_5k_time", "5K run time", "mm:ss", "30:00"),
        _num("pull_ups", "Strict pull-ups in one set", "reps", 0, 50, 1, None, 2),
        _num("dead_hang_s", "Dead hang", "seconds", 0, 300, 5, "Grip strength for rigs and monkey bars", 30),
        _num("sessions_per_week", "Training sessions per week", "sessions", 0, 14, 1, None, 3),
    ],
    "court": [
        _choice("level", "Your playing level", LEVEL_CHOICES, None, "intermediate"),
        _num("sessions_per_week", "Sessions per week", "sessions", 0, 14, 1, "Practice or coaching", 2),
        _num("matches_per_month", "Competitive matches per month", "matches", 0, 60, 1, "Scored games, not drills", 4),
        _num("longest_play_min", "Longest continuous play you can sustain", "min", 0, 300, 5, None, 60),
        _num("years_playing", "Years playing", "years", 0, 60, 0.5, None, 2),
    ],
    "team": [
        _choice("level", "Your team's level", LEVEL_CHOICES, None, "intermediate"),
        _num("squad_size", "Players in your squad", "players", 1, 30, 1, None, 8),
        _num("sessions_per_week", "Team sessions per week", "sessions", 0, 7, 1, None, 1),
        _num("matches_per_month", "Matches per month", "matches", 0, 30, 1, None, 2),
        _num("full_intensity_min", "Minutes you can play at full intensity", "min", 0, 120, 5, None, 30),
    ],
}


def form_family(sport) -> str:
    if sport.slug == "trail-running":
        return "trail"
    return sport.family


def form_for(sport, prefill: dict | None = None) -> dict:
    fam = form_family(sport)
    fields = FORMS[fam]
    defaults = {f["id"]: f.get("default") for f in fields}
    for k, v in (prefill or {}).items():
        if k in defaults and v is not None:
            defaults[k] = v
    return {"family": fam, "fields": fields, "defaults": defaults}


# --------------------------------------------------------------------------
# input handling
# --------------------------------------------------------------------------


def _clean(fam: str, inputs: dict) -> dict:
    out = {}
    for f in FORMS[fam]:
        raw = inputs.get(f["id"], f.get("default"))
        if raw is None or raw == "":
            raise ReadinessError(f"'{f['label']}' is required")
        if f["type"] == "number":
            try:
                val = float(raw)
            except (TypeError, ValueError) as exc:
                raise ReadinessError(f"'{f['label']}' must be a number") from exc
            if val < f["min"] or val > f["max"]:
                raise ReadinessError(f"'{f['label']}' must be between {f['min']} and {f['max']}")
            out[f["id"]] = val
        elif f["type"] == "duration":
            secs = parse_duration(str(raw))
            if not secs or secs <= 0:
                raise ReadinessError(f"'{f['label']}' must look like mm:ss or h:mm:ss")
            out[f["id"]] = secs
        else:
            values = {o["value"] for o in f["options"]}
            if str(raw) not in values:
                raise ReadinessError(f"'{f['label']}' has an unknown value")
            out[f["id"]] = str(raw)
    return out


def _interp(points: list[tuple[float, float]], x: float) -> float:
    """Piecewise-linear interpolation, clamped at both ends."""
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:], strict=False):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def _ratio(have: float, need: float) -> float:
    if need <= 0:
        return 1.0
    return max(0.0, min(1.0, have / need))


def _cutoff_score(pred: float | None, cutoff_min: int | None) -> tuple[float | None, float | None]:
    """Map the predicted finish against the cutoff. 15%+ spare time scores full marks."""
    if pred is None or not cutoff_min:
        return None, None
    cutoff = cutoff_min * 60
    margin = (cutoff - pred) / cutoff
    if margin >= 0.15:
        s = 1.0
    elif margin >= 0:
        s = 0.45 + 0.55 * margin / 0.15
    else:
        s = max(0.0, 0.45 + margin * 3)
    return s, margin


def _verdict(score: float) -> tuple[str, str]:
    for threshold, key, label in VERDICTS:
        if score >= threshold:
            return key, label
    return VERDICTS[-1][1], VERDICTS[-1][2]


def _combine(components: list[dict]) -> int:
    used = [c for c in components if c["score"] is not None]
    total_w = sum(c["weight"] for c in used) or 1
    return int(round(sum(c["score"] * c["weight"] for c in used) / total_w))


def _weeks(n):
    """'Under a week', '1 week' or 'N weeks'."""
    if n < 1:
        return "Under a week"
    return "1 week" if n == 1 else f"{n} weeks"


def _component(key, label, frac, weight, detail):
    return {
        "key": key,
        "label": label,
        "score": None if frac is None else int(round(frac * 100)),
        "weight": weight,
        "detail": detail,
    }


def _fmt_km(km: float) -> str:
    return f"{km:.1f}".rstrip("0").rstrip(".") + " km"


def _round_display(v: float) -> str:
    if v >= 100:
        return f"{round(v, -1):.0f}"
    return f"{v:.0f}" if v >= 10 else f"{v:.1f}".rstrip("0").rstrip(".")


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


# --------------------------------------------------------------------------
# progression plans
# --------------------------------------------------------------------------


def _progression_plan(
    today: date,
    event_date: date,
    start: float,
    target: float,
    unit: str,
    label: str,
    taper_weeks: int,
    step_pct: float = 0.10,
    step_min: float = 1.0,
    extra=None,
    scale: float = 1.0,
) -> dict:
    """Long-session progression: +step_pct a week (at least step_min), a cutback every 4th
    week, then a taper. Returns at most 26 rows; longer runways start with a base phase."""
    weeks = max(0, (event_date - today).days // 7)
    rows = []
    if weeks == 0:
        return {
            "weeks": 0,
            "rows": [
                {
                    "week": 0,
                    "start": today.isoformat(),
                    "phase": "Race week",
                    "target": "Rest, short shakeouts",
                    "note": "Too late to build: keep it easy",
                }
            ],
        }
    build_weeks = max(0, weeks - taper_weeks)
    cur = max(start, step_min)
    peak = cur
    first_monday = _monday(today) + timedelta(days=7) if today.weekday() > 2 else _monday(today)
    for w in range(1, weeks + 1):
        wk_start = first_monday + timedelta(days=7 * (w - 1))
        if w <= build_weeks:
            if w % 4 == 0:
                phase = "Cutback"
                val = peak * 0.8
            else:
                phase = "Build" if cur < target else "Hold"
                cur = min(target, max(cur * (1 + step_pct), cur + step_min)) if w > 1 else cur
                peak = max(peak, cur)
                val = cur
                if cur >= target:
                    phase = "Peak" if w > build_weeks - 3 else "Hold"
        elif w < weeks:
            phase = "Taper"
            val = peak * (0.75 if w == build_weeks + 1 else 0.55)
        else:
            phase = "Race week"
            val = None
        row = {
            "week": w,
            "start": wk_start.isoformat(),
            "phase": phase,
            "target": f"{label} {_round_display(val * scale)} {unit}"
            if val is not None
            else "Short easy sessions, then race",
            "note": None,
        }
        if extra:
            row["note"] = extra(w, phase)
        rows.append(row)
    if len(rows) > 26:
        head = rows[: len(rows) - 24]
        rows = [
            {
                "week": f"1-{len(head)}",
                "start": head[0]["start"],
                "phase": "Base",
                "target": f"{label} around {_round_display(start * scale)} {unit}, build consistency",
                "note": "Easy volume first",
            }
        ] + rows[len(head) :]
    reached = peak >= target * 0.98
    return {"weeks": weeks, "rows": rows, "reaches_target": reached, "target": round(target, 1)}


def _template_plan(today: date, event_date: date, focus: list[str], taper_note: str) -> dict:
    weeks = max(0, (event_date - today).days // 7)
    if weeks == 0:
        return {
            "weeks": 0,
            "rows": [{"week": 0, "start": today.isoformat(), "phase": "Race week", "target": taper_note, "note": None}],
        }
    first_monday = _monday(today) + timedelta(days=7) if today.weekday() > 2 else _monday(today)
    rows = []
    for w in range(1, weeks + 1):
        phase = "Race week" if w == weeks else "Sharpen" if w == weeks - 1 else "Build"
        rows.append(
            {
                "week": w,
                "start": (first_monday + timedelta(days=7 * (w - 1))).isoformat(),
                "phase": phase,
                "target": taper_note if phase == "Race week" else focus[(w - 1) % len(focus)],
                "note": None,
            }
        )
    if len(rows) > 12:
        rows = [
            {
                "week": f"1-{len(rows) - 10}",
                "start": rows[0]["start"],
                "phase": "Base",
                "target": "Consistent training and regular match play",
                "note": None,
            }
        ] + rows[-10:]
    return {"weeks": weeks, "rows": rows}


# --------------------------------------------------------------------------
# endurance assessors
# --------------------------------------------------------------------------

# Long run you want to have done before race day, by race distance (km).
# 5K/10K: cover the distance. Half: 16 km (10 mile novice peak). Marathon: 32 km
# (20 mile novice peak). Ultras: back-to-back weekends instead of one huge run.
LONG_RUN = [(5, 5), (10, 10), (21.1, 16), (42.2, 32), (50, 35), (100, 45), (160, 50)]
# Weekly volume (km) that a finisher typically carries in the final build weeks.
WEEKLY_RUN = [(5, 12), (10, 20), (21.1, 30), (42.2, 45), (50, 55), (100, 70), (160, 80)]
TAPER_WEEKS = [(10, 1), (21.1, 2), (42.2, 3)]


def _riegel(t1: float, d1: float, d2: float, exponent: float = 1.06) -> float:
    return t1 * (d2 / d1) ** exponent


def _assess_run(event, cat, x: dict, today: date, trail: bool) -> dict:
    dist = cat.distance_km or 10.0
    gain = (event.course or {}).get("elevation_gain_m") if trail else None
    # ITRA effort distance: 100 m of climbing costs about the same as 1 km on the flat
    effort = dist + (gain or 0) / 100

    need_long = _interp(LONG_RUN, effort)
    need_weekly = _interp(WEEKLY_RUN, effort)
    long_frac = _ratio(x["longest_run_km"], need_long)
    vol_frac = _ratio(x["weekly_km"], need_weekly)

    # Riegel prediction, with a slightly steeper exponent for under-trained runners
    # at half marathon and beyond, where low mileage costs most.
    d1 = float(x["recent_distance"])
    exponent = 1.06
    if effort >= 21.1:
        exponent += 0.04 * (1 - vol_frac)
    pred = _riegel(x["recent_time"], d1, effort, exponent)
    if trail:
        pred *= 1.10  # technical terrain, footing, aid-station stops
    cut_frac, margin = _cutoff_score(pred, cat.cutoff_minutes)

    taper = int(_interp(TAPER_WEEKS, effort)) if effort >= 10 else 1
    plan = _progression_plan(
        today, event.start_date, x["longest_run_km"], need_long, "km", "Long run", taper, 0.10, 1.5
    )
    weeks = plan["weeks"]
    runway_frac = 1.0 if plan.get("reaches_target", True) else _ratio(weeks, weeks + 4)
    if x["longest_run_km"] >= need_long:
        runway_frac = 1.0

    comps = [
        _component(
            "endurance",
            "Long run",
            long_frac,
            0.35,
            f"Longest run {x['longest_run_km']:g} km. Before race day aim for about {need_long:.0f} km.",
        ),
        _component(
            "volume",
            "Weekly volume",
            vol_frac,
            0.25,
            f"{x['weekly_km']:g} km a week. Finishers of this distance usually carry about {need_weekly:.0f} km.",
        ),
        _component(
            "runway",
            "Time to prepare",
            runway_frac,
            0.20,
            f"{_weeks(weeks)} to go. "
            + (
                "Enough to reach your peak long run safely."
                if runway_frac >= 1
                else "Not enough to reach your peak long run at +10% a week."
            ),
        ),
    ]
    if cut_frac is not None:
        comps.append(
            _component(
                "cutoff",
                "Cutoff margin",
                cut_frac,
                0.20,
                f"Predicted {format_seconds(pred)} against a {format_seconds(cat.cutoff_minutes * 60)} cutoff.",
            )
        )
    if trail:
        need_climb = (gain or 0) * 0.5
        climb_frac = _ratio(x["climb_m"], need_climb) if need_climb else None
        comps.append(
            _component(
                "climbing",
                "Climbing",
                climb_frac,
                0.15,
                f"Course climbs about {gain:.0f} m; your biggest single-run climb is {x['climb_m']:.0f} m."
                if gain
                else "Elevation not published for this course.",
            )
        )

    gaps = []
    if long_frac < 1:
        gaps.append(
            f"Build your long run from {x['longest_run_km']:g} km to {need_long:.0f} km, adding about "
            "10% a week with an easier week every fourth week."
        )
    if vol_frac < 0.85:
        gaps.append(f"Raise weekly distance towards {need_weekly:.0f} km by adding easy runs, not by running faster.")
    if margin is not None and margin < 0.1:
        gaps.append(
            "Your predicted time is close to the cutoff: practise run-walk intervals and pace the first half "
            "conservatively."
        )
    if trail and gain and x["climb_m"] < gain * 0.5:
        gaps.append("Add a weekly hill session or stair workout, and practise power-hiking the steep parts.")
    if not trail and x["runs_per_week"] < 3 and effort >= 10:
        gaps.append("Three runs a week is the minimum most plans use for this distance.")

    pace = pred / dist if dist else None
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(pred),
            "finish_label": format_seconds(pred),
            "range_label": f"{format_seconds(pred * 0.96)} to {format_seconds(pred * 1.05)}",
            "pace_label": f"{format_seconds(pace)} /km" if pace else None,
            "cutoff_label": format_seconds(cat.cutoff_minutes * 60) if cat.cutoff_minutes else None,
            "margin_pct": None if margin is None else round(margin * 100),
            "method": "Riegel formula from your recent race" + (", effort distance from ITRA" if trail else ""),
            "splits": [],
        },
        "plan": plan,
    }


# ACP / Audax time limits for brevets, hours.
BREVET_LIMIT_H = {200: 13.5, 300: 20, 400: 27, 600: 40, 1000: 75, 1200: 90}
PROFILE_SPEED = {"flat": 1.0, "rolling": 0.92, "hilly": 0.82, "mountain": 0.7}
LONG_RIDE = [(25, 15), (50, 35), (100, 70), (200, 130), (300, 200), (400, 250), (600, 300), (1200, 400)]
WEEKLY_RIDE = [(25, 30), (50, 50), (100, 90), (200, 130), (300, 160), (600, 200), (1200, 250)]


def _assess_ride(event, cat, x: dict, today: date) -> dict:
    dist = cat.distance_km or 50.0
    course = event.course or {}
    profile = course.get("profile") or "rolling"
    gain = course.get("elevation_gain_m")
    need_long = _interp(LONG_RIDE, dist)
    need_weekly = _interp(WEEKLY_RIDE, dist)
    long_frac = _ratio(x["longest_ride_km"], need_long)
    vol_frac = _ratio(x["weekly_km"], need_weekly)

    speed = x["avg_speed_kmh"] * PROFILE_SPEED.get(profile, 0.92)
    if dist > x["longest_ride_km"]:
        speed *= 0.94  # fatigue beyond your longest ride
    moving = dist / speed * 3600
    is_brevet = event.discipline == "brevet"
    stops = 0.18 if is_brevet else 0.06
    pred = moving * (1 + stops)
    cutoff_min = cat.cutoff_minutes
    if not cutoff_min and is_brevet:
        nearest = min(BREVET_LIMIT_H, key=lambda k: abs(k - dist))
        if abs(nearest - dist) <= 30:
            cutoff_min = int(BREVET_LIMIT_H[nearest] * 60)
    cut_frac, margin = _cutoff_score(pred, cutoff_min)

    plan = _progression_plan(
        today, event.start_date, x["longest_ride_km"], need_long, "km", "Long ride", 1 if dist < 150 else 2, 0.12, 10
    )
    weeks = plan["weeks"]
    runway_frac = 1.0 if plan.get("reaches_target", True) or long_frac >= 1 else _ratio(weeks, weeks + 4)

    comps = [
        _component(
            "endurance",
            "Long ride",
            long_frac,
            0.35,
            f"Longest ride {x['longest_ride_km']:g} km. Aim for about {need_long:.0f} km before the event.",
        ),
        _component(
            "volume",
            "Weekly distance",
            vol_frac,
            0.20,
            f"{x['weekly_km']:g} km a week against about {need_weekly:.0f} km for this distance.",
        ),
        _component("runway", "Time to prepare", runway_frac, 0.20, f"{_weeks(weeks)} to go."),
    ]
    if cut_frac is not None:
        comps.append(
            _component(
                "cutoff",
                "Time limit",
                cut_frac,
                0.25,
                f"Estimated {format_seconds(pred)} including stops, limit {format_seconds(cutoff_min * 60)}.",
            )
        )
    if gain:
        comps.append(
            _component(
                "climbing",
                "Climbing",
                _ratio(x["climb_m"], gain * 0.5),
                0.15,
                f"Course gains about {gain:.0f} m; your biggest ride climbed {x['climb_m']:.0f} m.",
            )
        )

    gaps = []
    if long_frac < 1:
        gaps.append(
            f"Extend your long ride from {x['longest_ride_km']:g} km to about {need_long:.0f} km, "
            "practising eating every 45 minutes on the bike."
        )
    if is_brevet:
        gaps.append(
            "Brevets are self-supported: carry lights, a reflective vest, spares and a brevet card, "
            "and plan your control stops."
        )
    if margin is not None and margin < 0.1:
        gaps.append("You are close to the time limit: cut stop time first, it is the cheapest speed you will find.")
    if gain and x["climb_m"] < gain * 0.5:
        gaps.append("Add a weekly climbing ride and practise steady seated climbing.")

    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(pred),
            "finish_label": format_seconds(pred),
            "range_label": f"{format_seconds(pred * 0.93)} to {format_seconds(pred * 1.10)}",
            "pace_label": f"{dist / (pred / 3600):.1f} km/h overall",
            "cutoff_label": format_seconds(cutoff_min * 60) if cutoff_min else None,
            "margin_pct": None if margin is None else round(margin * 100),
            "method": f"Your average speed, adjusted for a {profile} course and stop time",
            "splits": [],
        },
        "plan": plan,
    }


# Open water costs time against pool pace: no walls to push off, sighting, chop.
OPEN_WATER_FACTOR = {"pool": 1.0, "lake": 1.06, "river": 1.06, "sea": 1.12, "open-water": 1.10}


def _water(event) -> str:
    course = event.course or {}
    surface = (course.get("surface") or "").lower()
    terrain = course.get("terrain")
    if terrain == "pool" or "pool" in surface:
        return "pool"
    for w in ("sea", "lake", "river"):
        if w in surface or w in (course.get("description") or "").lower():
            return w
    return "open-water" if terrain in ("open-water", "mixed") else "pool"


def _assess_swim(event, cat, x: dict, today: date) -> dict:
    dist = cat.swim_km or cat.distance_km or 1.0
    water = _water(event)
    pred = dist * 10 * x["pace_100m"] * OPEN_WATER_FACTOR[water]
    cut_frac, margin = _cutoff_score(pred, cat.cutoff_minutes)
    need = dist * 1000 * (1.0 if dist <= 5 else 0.8)
    long_frac = _ratio(x["longest_swim_m"], need)
    ow = x["open_water_swims"]
    ow_frac = None if water == "pool" else (0.2 if ow == 0 else 0.6 if ow < 3 else 1.0)
    freq_frac = _ratio(x["sessions_per_week"], 3 if dist > 1.5 else 2)

    plan = _progression_plan(
        today,
        event.start_date,
        x["longest_swim_m"] / 1000,
        need / 1000 * 1.1,
        "m",
        "Longest swim",
        1,
        0.12,
        0.1,
        scale=1000,
    )
    weeks = plan["weeks"]
    runway_frac = 1.0 if plan.get("reaches_target", True) or long_frac >= 1 else _ratio(weeks, weeks + 4)

    comps = [
        _component(
            "endurance",
            "Non-stop distance",
            long_frac,
            0.35,
            f"You swim {x['longest_swim_m']:.0f} m non-stop; this race is {dist * 1000:.0f} m.",
        ),
        _component("frequency", "Swim frequency", freq_frac, 0.15, f"{x['sessions_per_week']:g} sessions a week."),
        _component("runway", "Time to prepare", runway_frac, 0.15, f"{_weeks(weeks)} to go."),
    ]
    if ow_frac is not None:
        comps.append(
            _component(
                "open_water",
                "Open-water practice",
                ow_frac,
                0.20,
                f"{ow:g} open-water swims recently. Sighting and waves change everything.",
            )
        )
    if cut_frac is not None:
        comps.append(
            _component(
                "cutoff",
                "Cutoff margin",
                cut_frac,
                0.20,
                f"Estimated {format_seconds(pred)} against {format_seconds(cat.cutoff_minutes * 60)}.",
            )
        )
    gaps = []
    if long_frac < 1:
        gaps.append(f"Build your continuous swim to {need:.0f} m, adding 10-15% a week.")
    if ow_frac is not None and ow < 3:
        gaps.append(
            "Do at least three supervised open-water swims before race day: practise sighting every "
            "6-8 strokes and swimming in a group."
        )
    if margin is not None and margin < 0.1:
        gaps.append("You are close to the cutoff: work on steady pacing and drafting legally behind other swimmers.")
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(pred),
            "finish_label": format_seconds(pred),
            "range_label": f"{format_seconds(pred * 0.95)} to {format_seconds(pred * 1.08)}",
            "pace_label": f"{format_seconds(pred / (dist * 10))} /100 m",
            "cutoff_label": format_seconds(cat.cutoff_minutes * 60) if cat.cutoff_minutes else None,
            "margin_pct": None if margin is None else round(margin * 100),
            "method": f"Pool pace adjusted for {water.replace('-', ' ')} conditions",
            "splits": [],
        },
        "plan": plan,
    }


# IRONMAN-branded race cutoffs (hours): swim, swim+bike, overall.
TRI_CUTOFFS_H = {3: (1 + 10 / 60, 5.5, 8.5), 4: (2 + 20 / 60, 10.5, 17.0)}
TRANSITIONS_MIN = [4, 5, 7, 10, 14]


def _assess_tri(event, cat, x: dict, today: date) -> dict:
    cls = tri_class(cat)
    swim_km = cat.swim_km or 0
    bike_km = cat.bike_km or 0
    run_km = cat.run_km or 0
    if not (swim_km or bike_km or run_km):
        swim_km, bike_km, run_km = [(0.4, 10, 2.5), (0.75, 20, 5), (1.5, 40, 10), (1.9, 90, 21.1), (3.8, 180, 42.2)][
            cls
        ]
    water = _water(event)
    swim = swim_km * 10 * x["swim_pace_100m"] * OPEN_WATER_FACTOR.get(water, 1.08) if swim_km else 0
    bike = bike_km / (x["bike_speed_kmh"] * (0.97 if bike_km > 60 else 1.0)) * 3600 if bike_km else 0
    # running off the bike: about 5% slower for short races, more as the day gets longer
    off_bike = [1.04, 1.05, 1.07, 1.12, 1.20][cls]
    run = _riegel(x["run_10k_time"], 10, run_km) * off_bike if run_km else 0
    transitions = TRANSITIONS_MIN[cls] * 60
    total = swim + bike + run + transitions

    cutoff_min = cat.cutoff_minutes
    cut_parts = TRI_CUTOFFS_H.get(cls) if "ironman" in event.name.lower() else None
    if not cutoff_min and cut_parts:
        cutoff_min = int(cut_parts[2] * 60)
    cut_frac, margin = _cutoff_score(total, cutoff_min)

    swim_frac = _ratio(x["longest_swim_m"], swim_km * 1000) if swim_km else None
    bike_frac = _ratio(x["longest_ride_km"], bike_km * 0.9) if bike_km else None
    run_need = run_km if run_km <= 10 else max(10, run_km * 0.75)
    run_frac = _ratio(x["longest_run_km"], run_need) if run_km else None
    comps = []
    if swim_frac is not None:
        comps.append(
            _component(
                "swim",
                "Swim",
                swim_frac,
                0.25,
                f"{x['longest_swim_m']:.0f} m non-stop against a {swim_km * 1000:.0f} m swim.",
            )
        )
    if bike_frac is not None:
        comps.append(
            _component(
                "bike", "Bike", bike_frac, 0.25, f"Longest ride {x['longest_ride_km']:g} km against {bike_km:g} km."
            )
        )
    if run_frac is not None:
        comps.append(
            _component(
                "run",
                "Run",
                run_frac,
                0.25,
                f"Longest run {x['longest_run_km']:g} km; aim for {run_need:.0f} km before race day.",
            )
        )
    weeks = max(0, (event.start_date - today).days // 7)
    need_weeks = [8, 10, 14, 20, 30][cls]
    comps.append(
        _component(
            "runway",
            "Time to prepare",
            _ratio(weeks, need_weeks),
            0.15,
            f"{_weeks(weeks)} to go; a typical {['short', 'sprint', 'olympic', '70.3', 'full'][cls]} "
            f"build is about {need_weeks} weeks.",
        )
    )
    if cut_frac is not None:
        comps.append(
            _component(
                "cutoff",
                "Cutoff margin",
                cut_frac,
                0.20,
                f"Estimated {format_seconds(total)} against {format_seconds(cutoff_min * 60)}.",
            )
        )
    elif water != "pool" and swim_km:
        ow = x["open_water_swims"]
        comps.append(
            _component(
                "open_water",
                "Open-water practice",
                0.2 if ow == 0 else 0.6 if ow < 3 else 1.0,
                0.15,
                f"{ow:g} open-water swims in the last 3 months.",
            )
        )

    gaps = []
    weakest = min((c for c in comps if c["key"] in ("swim", "bike", "run")), key=lambda c: c["score"], default=None)
    if weakest and weakest["score"] < 100:
        gaps.append(f"Your {weakest['label'].lower()} is the limiter: give it an extra session each week.")
    if cut_parts and swim > cut_parts[0] * 3600 * 0.85:
        gaps.append("Your swim is near the swim cutoff. Prioritise swim fitness and open-water sighting.")
    if water != "pool" and swim_km and x["open_water_swims"] < 3:
        gaps.append("Practise mass-start open-water swims and wetsuit-free sea swimming before race day.")
    gaps.append("Rehearse transitions and do at least one brick session (bike straight into a run) every week.")

    plan = _template_plan(
        today,
        event.start_date,
        [
            "Swim technique + long ride + short brick run",
            "Swim endurance + bike intervals + long run",
            "Open-water swim + long ride + brick",
            "Recovery week: shorter sessions, keep frequency",
        ],
        "Short sessions, check bike, rest two days before",
    )
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(total),
            "finish_label": format_seconds(total),
            "range_label": f"{format_seconds(total * 0.95)} to {format_seconds(total * 1.08)}",
            "pace_label": None,
            "cutoff_label": format_seconds(cutoff_min * 60) if cutoff_min else None,
            "margin_pct": None if margin is None else round(margin * 100),
            "method": "Sum of your swim, bike and run estimates plus transitions",
            "splits": [
                s
                for s in (
                    {"label": "Swim", "seconds": int(swim), "value": format_seconds(swim)} if swim else None,
                    {"label": "T1 + T2", "seconds": transitions, "value": format_seconds(transitions)},
                    {"label": "Bike", "seconds": int(bike), "value": format_seconds(bike)} if bike else None,
                    {"label": "Run", "seconds": int(run), "value": format_seconds(run)} if run else None,
                )
                if s
            ],
        },
        "plan": plan,
    }


STATION_MIN = {"new": 46, "some": 36, "strong": 28}


def _assess_hyrox(event, cat, x: dict, today: date) -> dict:
    name = cat.name.lower()
    pro = "pro" in name
    doubles = "double" in name
    relay = "relay" in name
    pace = x["run_5k_time"] / 5
    # "compromised running": 1 km repeats between stations run well below fresh pace
    runs = 8 * pace * 1.22
    stations = STATION_MIN[x["stations"]] * 60 * (1.18 if pro else 1.0)
    roxzone = 8 * 60
    if doubles:
        stations *= 0.62
    total = runs + stations + roxzone
    if relay:
        total = total * 0.42
    lvl = {"new": 0.35, "some": 0.7, "strong": 1.0}[x["stations"]]
    # 5K at 4:00 /km scores full marks, 8:00 /km about a third
    run_frac = max(0.2, min(1.0, 1 - 0.65 * (pace - 240) / 240))
    wb_need = 100 if not doubles else 50
    comps = [
        _component(
            "running",
            "Running engine",
            run_frac,
            0.30,
            f"5K in {format_seconds(x['run_5k_time'])}: "
            f"8 x 1 km repeats come out near {format_seconds(pace * 1.22)} /km.",
        ),
        _component("stations", "Station strength", lvl, 0.30, "Sleds, lunges and wall balls decide most finishes."),
        _component(
            "wall_balls",
            "Wall balls",
            _ratio(x["wall_balls"], wb_need * 0.4),
            0.15,
            f"{x['wall_balls']:.0f} unbroken; the final station is {wb_need} reps.",
        ),
        _component(
            "frequency",
            "Training frequency",
            _ratio(x["sessions_per_week"], 4),
            0.10,
            f"{x['sessions_per_week']:g} sessions a week.",
        ),
    ]
    weeks = max(0, (event.start_date - today).days // 7)
    comps.append(_component("runway", "Time to prepare", _ratio(weeks, 8), 0.15, f"{_weeks(weeks)} to go."))
    gaps = []
    if x["stations"] != "strong":
        gaps.append("Practise every station at race weight at least once a fortnight, especially sled push and pull.")
    if x["wall_balls"] < wb_need * 0.4:
        gaps.append("Build wall-ball capacity in sets of 20-25 with short rests.")
    gaps.append("Do 'compromised' sessions: 1 km run straight after a station, repeated 4-8 times.")
    plan = _template_plan(
        today,
        event.start_date,
        [
            "Run intervals + sled and lunge strength",
            "Compromised running: 1 km + station x 4",
            "Long easy run + wall balls and burpee broad jumps",
            "Full or half simulation at race weights",
        ],
        "Light shakeout, rehearse transitions, rest",
    )
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(total),
            "finish_label": format_seconds(total),
            "range_label": f"{format_seconds(total * 0.93)} to {format_seconds(total * 1.10)}",
            "pace_label": None,
            "cutoff_label": None,
            "margin_pct": None,
            "method": "8 x 1 km at compromised pace, station time by experience, plus Roxzone",
            "splits": [
                {"label": "Runs", "seconds": int(runs), "value": format_seconds(runs)},
                {"label": "Stations", "seconds": int(stations), "value": format_seconds(stations)},
                {"label": "Roxzone", "seconds": roxzone, "value": format_seconds(roxzone)},
            ]
            if not relay
            else [],
        },
        "plan": plan,
    }


def _assess_ocr(event, cat, x: dict, today: date) -> dict:
    dist = cat.distance_km or 5.0
    run_time = _riegel(x["run_5k_time"], 5, dist)
    obstacles = 3 * dist  # Devils Circuit style: about 15 obstacles over 5 km
    grip = _ratio(x["dead_hang_s"], 60)
    pulls = _ratio(x["pull_ups"], 6)
    pred = run_time * 1.25 + obstacles * 60 * (1.6 - 0.6 * (grip + pulls) / 2)
    competitive = "compet" in cat.name.lower() or cat.level == "advanced"
    comps = [
        _component(
            "running",
            "Running",
            1.0 if x["run_5k_time"] <= 1800 else _ratio(1800, x["run_5k_time"]),
            0.30,
            f"5K in {format_seconds(x['run_5k_time'])}.",
        ),
        _component(
            "pulling",
            "Pulling strength",
            pulls,
            0.25 if competitive else 0.2,
            f"{x['pull_ups']:.0f} strict pull-ups; walls and rigs reward 5+.",
        ),
        _component(
            "grip", "Grip", grip, 0.25 if competitive else 0.2, f"{x['dead_hang_s']:.0f}s dead hang; aim for 60s."
        ),
        _component(
            "frequency",
            "Training frequency",
            _ratio(x["sessions_per_week"], 3),
            0.10,
            f"{x['sessions_per_week']:g} sessions a week.",
        ),
    ]
    weeks = max(0, (event.start_date - today).days // 7)
    comps.append(_component("runway", "Time to prepare", _ratio(weeks, 6), 0.20, f"{_weeks(weeks)} to go."))
    gaps = []
    if x["pull_ups"] < 5:
        gaps.append("Work towards 5 strict pull-ups: negatives and band-assisted sets three times a week.")
    if x["dead_hang_s"] < 60:
        gaps.append("Add dead hangs and farmer carries for grip; monkey bars are mostly grip endurance.")
    gaps.append("Run on grass and trails, and practise getting up and over a wall with a partner.")
    plan = _template_plan(
        today,
        event.start_date,
        [
            "Intervals + pull-up and grip strength",
            "Trail run + carries and crawls",
            "Hill repeats + wall and rope practice",
            "Easy run + mobility",
        ],
        "Easy run, rest, lay out kit",
    )
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": {
            "finish_seconds": int(pred),
            "finish_label": format_seconds(pred),
            "range_label": f"{format_seconds(pred * 0.9)} to {format_seconds(pred * 1.15)}",
            "pace_label": None,
            "cutoff_label": None,
            "margin_pct": None,
            "method": "Your 5K on rough terrain plus about a minute per obstacle, scaled by grip and pulling",
            "splits": [],
        },
        "plan": plan,
    }


# --------------------------------------------------------------------------
# court and team sports
# --------------------------------------------------------------------------

# Typical tournament-day load at amateur events: matches in a day x minutes each.
DAY_LOAD = {
    "badminton": (3, 30, "3 matches of about 30 min"),
    "tennis": (2, 90, "2 best-of-3-set matches of about 90 min"),
    "pickleball": (5, 18, "4-6 round-robin games of about 15-20 min"),
    "table-tennis": (4, 20, "group stage of 3-5 best-of-5 matches"),
    "squash": (2, 40, "1-2 best-of-5 matches of about 40 min"),
}
TEAM_FORMAT = {
    # format: (players on field, recommended squad, match minutes)
    "3x3": (3, 4, 10),
    "5v5": (5, 10, 40),
    "5-a-side": (5, 8, 40),
    "6-a-side": (6, 9, 40),
    "7-a-side": (7, 10, 50),
    "11-a-side": (11, 16, 80),
}


def _assess_court(event, cat, x: dict, today: date, sport_slug: str) -> dict:
    lvl = {"beginner": 0, "intermediate": 1, "advanced": 2}[x["level"]]
    ci = level_index(cat.level, "court")
    rb = rating_bracket(cat)
    skill = 1.0 if ci is None else {0: 1.0, -1: 0.85, -2: 0.6, 1: 0.55, 2: 0.15}[ci - lvl]
    n, minutes, desc = DAY_LOAD.get(sport_slug, (3, 30, "a few matches"))
    day_minutes = n * minutes
    endurance = _ratio(x["longest_play_min"], day_minutes * 0.6)
    target_matches = [2, 4, 8][ci if ci is not None else 1]
    practice = _ratio(x["matches_per_month"], target_matches)
    training = _ratio(x["sessions_per_week"], [1, 2, 3][ci if ci is not None else 1])
    weeks = max(0, (event.start_date - today).days // 7)
    comps = [
        _component(
            "skill",
            "Draw fit",
            skill,
            0.35,
            f"This draw is pitched at {cat.level} level"
            + (f" ({rb[0]} rating)" if rb else "")
            + f"; you play at {x['level']} level.",
        ),
        _component(
            "match_play",
            "Match practice",
            practice,
            0.25,
            f"{x['matches_per_month']:g} competitive matches a month; aim for {target_matches}.",
        ),
        _component(
            "endurance",
            "Tournament-day stamina",
            endurance,
            0.20,
            f"A typical day here is {desc}. You can sustain {x['longest_play_min']:.0f} min.",
        ),
        _component("training", "Training", training, 0.10, f"{x['sessions_per_week']:g} sessions a week."),
        _component("runway", "Time to prepare", _ratio(weeks, 3), 0.10, f"{_weeks(weeks)} to go."),
    ]
    gaps = []
    if skill < 0.6:
        gaps.append("This draw is above your level: look for a lower or rated draw at the same event.")
    if practice < 1:
        gaps.append(
            f"Play {target_matches} scored matches a month: tournament nerves fade with match play, not drills."
        )
    if endurance < 1:
        gaps.append(f"Build stamina for {desc}: play back-to-back matches with short breaks in practice.")
    if x["years_playing"] < 1:
        gaps.append("Learn the scoring and service rules thoroughly; most first-tournament points are lost there.")
    plan = _template_plan(
        today,
        event.start_date,
        [
            "2 match-play sessions + footwork and agility",
            "Serve and return practice + conditioning",
            "Back-to-back matches to simulate a tournament day",
        ],
        "Light hit, check kit and draw timings, sleep well",
    )
    return {
        "components": comps,
        "gaps": gaps,
        "prediction": None,
        "plan": plan,
        "day_load": {"matches": n, "minutes_each": minutes, "description": desc},
    }


def _team_format(cat) -> str:
    from .categories import category_formats

    fmts = category_formats(cat)
    for f in ("3x3", "5-a-side", "6-a-side", "7-a-side", "11-a-side", "5v5"):
        if f in fmts:
            return f
    return "5v5" if "basket" in cat.name.lower() else "7-a-side"


def _assess_team(event, cat, x: dict, today: date, sport_slug: str) -> dict:
    fmt = "3x3" if sport_slug == "basketball" and "3x3" in cat.name.lower() else _team_format(cat)
    on_field, squad, minutes = TEAM_FORMAT.get(fmt, (7, 10, 50))
    lvl = {"beginner": 0, "intermediate": 1, "advanced": 2}[x["level"]]
    ci = level_index(cat.level, "team")
    skill = {0: 1.0, -1: 0.85, -2: 0.6, 1: 0.55, 2: 0.15}[(ci if ci is not None else 1) - lvl]
    squad_frac = 0.0 if x["squad_size"] < on_field else _ratio(x["squad_size"], squad)
    fitness = _ratio(x["full_intensity_min"], minutes * 0.6)
    weeks = max(0, (event.start_date - today).days // 7)
    comps = [
        _component(
            "squad",
            "Squad",
            squad_frac,
            0.25,
            f"{x['squad_size']:.0f} players; {fmt} needs {on_field} on court plus subs, about {squad} in all.",
        ),
        _component("skill", "Level fit", skill, 0.25, f"Division pitched at {cat.level} level."),
        _component(
            "fitness",
            "Match fitness",
            fitness,
            0.20,
            f"Matches run about {minutes} min; you can go hard for {x['full_intensity_min']:.0f}.",
        ),
        _component(
            "cohesion",
            "Playing together",
            _ratio(x["sessions_per_week"] + x["matches_per_month"] / 4, 2),
            0.20,
            f"{x['sessions_per_week']:g} team sessions a week, {x['matches_per_month']:g} matches a month.",
        ),
        _component("runway", "Time to prepare", _ratio(weeks, 3), 0.10, f"{_weeks(weeks)} to go."),
    ]
    gaps = []
    if x["squad_size"] < squad:
        gaps.append(f"Recruit to at least {squad} players: tournament days are hot and rolling subs win games.")
    if fitness < 1:
        gaps.append("Add repeated-sprint conditioning: 6-10 x 30 s hard with 30 s easy, twice a week.")
    gaps.append("Agree set pieces, kick-offs and who takes penalties before the day.")
    plan = _template_plan(
        today,
        event.start_date,
        [
            "Team session: shape and set pieces + sprint conditioning",
            "Friendly match + recovery",
            "Small-sided games + finishing",
        ],
        "Light session, confirm squad list and kit colours",
    )
    return {"components": comps, "gaps": gaps, "prediction": None, "plan": plan}


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def assess(event, cat, inputs: dict, today: date) -> dict:
    sport = event.sport
    fam = form_family(sport)
    x = _clean(fam, inputs)
    if event.start_date < today:
        raise ReadinessError("This event has already happened")
    if fam == "run":
        res = _assess_run(event, cat, x, today, trail=False)
    elif fam == "trail":
        res = _assess_run(event, cat, x, today, trail=True)
    elif fam == "ride":
        res = _assess_ride(event, cat, x, today)
    elif fam == "swim":
        res = _assess_swim(event, cat, x, today)
    elif fam == "tri":
        res = _assess_tri(event, cat, x, today)
    elif fam == "hyrox":
        res = _assess_hyrox(event, cat, x, today)
    elif fam == "ocr":
        res = _assess_ocr(event, cat, x, today)
    elif fam == "court":
        res = _assess_court(event, cat, x, today, sport.slug)
    else:
        res = _assess_team(event, cat, x, today, sport.slug)

    score = _combine(res["components"])
    key, label = _verdict(score)
    days = (event.start_date - today).days
    headline = {
        "ready": "You have the base for this one. Keep it consistent and taper well.",
        "nearly": "Close. Close the gaps below and you will be on the start line ready.",
        "build": "Possible, but you need a focused build. Start this week.",
        "not-this-one": "This one is too big a jump for now. Try a shorter category or a later event.",
    }[key]
    return {
        "score": score,
        "verdict": key,
        "verdict_label": label,
        "headline": headline,
        "days_to_event": days,
        "weeks_to_event": math.floor(days / 7),
        "inputs": {
            k: (format_seconds(v) if isinstance(v, int) and k.endswith(("time", "100m")) else v) for k, v in x.items()
        },
        **res,
    }
