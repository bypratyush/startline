"""Turn the raw research files in this folder into the app's seed catalogue.

    python3 research/build_seed.py

Reads   research/cities.json, research/content-*.json and the event files
Writes  backend/app/seed/data/cities.json, sports.json, events/<sport>.json

The research files are kept exactly as collected (with their source URLs).
This script only normalises them: slugs, units, cutoffs in minutes, and the
machine-readable attributes the recommender needs on every profile answer.
"""

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE.parent / "backend" / "app" / "seed" / "data"
EVENT_FILES = [
    "running-tier1.json",
    "running-tier2-trail.json",
    "tri-swim.json",
    "cycling-fitness-ocr.json",
    "racquet.json",
    "team-other.json",
]
DROPPED_SPORTS = {"basketball"}  # only one verifiable event: not enough to list the sport

# slug, display name, family, colour, order
SPORTS = [
    ("running", "Road running", "run", "#e4572e"),
    ("trail-running", "Trail & ultra", "run", "#557a33"),
    ("cycling", "Cycling", "ride", "#c98d00"),
    ("swimming", "Swimming", "swim", "#1e74d2"),
    ("triathlon", "Triathlon", "tri", "#6a47f0"),
    ("fitness-racing", "Fitness racing", "hyrox", "#d2336a"),
    ("ocr", "Obstacle racing", "ocr", "#8a5a2b"),
    ("badminton", "Badminton", "court", "#0f9b78"),
    ("tennis", "Tennis", "court", "#7a9500"),
    ("pickleball", "Pickleball", "court", "#00969f"),
    ("table-tennis", "Table tennis", "court", "#c4332c"),
    ("squash", "Squash", "court", "#4757d1"),
    ("football", "Football", "team", "#2c8a45"),
]

# --------------------------------------------------------------------------
# profile questions: research wording + machine-readable attributes
# --------------------------------------------------------------------------

LEVEL_PREFILL = {
    "running": {
        "beginner": {"weekly_km": 10, "runs_per_week": 3},
        "intermediate": {"weekly_km": 28, "runs_per_week": 4},
        "advanced": {"weekly_km": 50, "runs_per_week": 5},
    },
    "trail-running": {
        "beginner": {"weekly_km": 20},
        "intermediate": {"weekly_km": 35},
        "advanced": {"weekly_km": 55},
    },
    "cycling": {
        "beginner": {"weekly_km": 60, "climb_m": 150},
        "intermediate": {"weekly_km": 150, "climb_m": 600},
        "advanced": {"weekly_km": 260, "climb_m": 1200},
    },
    "swimming": {
        "beginner": {"pace_100m": "3:00", "sessions_per_week": 2},
        "intermediate": {"pace_100m": "2:20", "sessions_per_week": 3},
        "advanced": {"pace_100m": "1:50", "sessions_per_week": 4},
    },
    "triathlon": {
        "beginner": {"swim_pace_100m": "2:50", "longest_swim_m": 400, "bike_speed_kmh": 21, "longest_ride_km": 30,
                     "run_10k_time": "1:08:00", "longest_run_km": 6, "open_water_swims": 0},
        "intermediate": {"swim_pace_100m": "2:15", "longest_swim_m": 1200, "bike_speed_kmh": 26,
                         "longest_ride_km": 60, "run_10k_time": "55:00", "longest_run_km": 12, "open_water_swims": 2},
        "advanced": {"swim_pace_100m": "1:50", "longest_swim_m": 2200, "bike_speed_kmh": 30, "longest_ride_km": 100,
                     "run_10k_time": "45:00", "longest_run_km": 18, "open_water_swims": 6},
    },
    "fitness-racing": {
        "beginner": {"stations": "new", "sessions_per_week": 3, "wall_balls": 15},
        "intermediate": {"stations": "some", "sessions_per_week": 4, "wall_balls": 35},
        "advanced": {"stations": "strong", "sessions_per_week": 5, "wall_balls": 60},
    },
    "ocr": {
        "beginner": {"sessions_per_week": 2},
        "intermediate": {"sessions_per_week": 3},
        "advanced": {"sessions_per_week": 4},
    },
    "court": {
        "beginner": {"sessions_per_week": 1, "matches_per_month": 2, "longest_play_min": 45, "years_playing": 1},
        "intermediate": {"sessions_per_week": 2, "matches_per_month": 5, "longest_play_min": 75, "years_playing": 3},
        "advanced": {"sessions_per_week": 4, "matches_per_month": 10, "longest_play_min": 120, "years_playing": 7},
    },
    "football": {
        "beginner": {"sessions_per_week": 1, "matches_per_month": 2, "full_intensity_min": 20},
        "intermediate": {"sessions_per_week": 2, "matches_per_month": 4, "full_intensity_min": 35},
        "advanced": {"sessions_per_week": 3, "matches_per_month": 6, "full_intensity_min": 50},
    },
}

LEVEL_PROMPT = {
    "running": "How would you describe your running right now?",
    "trail-running": "How would you describe your trail running?",
    "cycling": "How would you describe your riding?",
    "swimming": "How would you describe your swimming?",
    "triathlon": "Where are you with triathlon?",
    "fitness-racing": "How would you describe your fitness racing?",
    "ocr": "How would you describe your obstacle racing?",
}

AGE_QUESTION = {
    "id": "age_group",
    "kind": "age",
    "prompt": "Which age group are you in?",
    "short": "Age group",
    "help": "Masters, seniors and veterans draws are split by age.",
    "options": [
        {"value": "u35", "label": "Under 35", "hint": "Open and age-free draws", "age": 28},
        {"value": "35-44", "label": "35 to 44", "hint": "Also eligible for 35+ masters draws", "age": 40},
        {"value": "45-54", "label": "45 to 54", "hint": "35+ and 45+ draws", "age": 50},
        {"value": "55+", "label": "55 and over", "hint": "Seniors and veterans draws", "age": 60},
    ],
}

HYROX_FORMAT = {
    "id": "division",
    "kind": "format",
    "prompt": "How do you want to race?",
    "short": "Division",
    "help": "Every HYROX format is 8 x 1 km runs, each followed by a workout station.",
    "options": [
        {"value": "solo", "label": "Solo", "hint": "Open or Pro: you do every run and every station", "formats": ["solo"]},
        {"value": "doubles", "label": "Doubles", "hint": "Run together, split the station work with a partner",
         "formats": ["pair", "doubles"]},
        {"value": "relay", "label": "Relay", "hint": "Team of four, each runs 2 km and does 2 stations",
         "formats": ["relay"]},
        {"value": "any", "label": "Not sure yet", "hint": "Show me every division", "formats": []},
    ],
}

# For each sport: list of (research question id or a dict for our own question, kind, applies_to, per-value attrs)
QUESTIONS = {
    "running": [
        "LEVEL",
        ("run_longest_recent", "capacity", "distance", {
            "none": {"capacity": 3, "prefill": {"longest_run_km": 2}},
            "lt5": {"capacity": 5, "prefill": {"longest_run_km": 4}},
            "5to10": {"capacity": 10, "prefill": {"longest_run_km": 8}},
            "11to21": {"capacity": 21.1, "prefill": {"longest_run_km": 16}},
            "gt21": {"capacity": 32, "prefill": {"longest_run_km": 25}},
        }),
        ("run_5k_band", "pace", None, {
            "none": {"prefill": {"recent_distance": "5", "recent_time": "40:00"}},
            "33to40": {"prefill": {"recent_distance": "5", "recent_time": "36:00"}},
            "27to33": {"prefill": {"recent_distance": "5", "recent_time": "30:00"}},
            "22to27": {"prefill": {"recent_distance": "5", "recent_time": "24:30"}},
            "lt22": {"prefill": {"recent_distance": "5", "recent_time": "20:30"}},
        }),
    ],
    "trail-running": [
        "LEVEL",
        ("trail_longest_finish", "capacity", "distance", {
            "none": {"capacity": 10, "experience": {"trail": 0}},
            "lt25": {"capacity": 25, "experience": {"trail": 1}},
            "25to50": {"capacity": 50, "experience": {"trail": 2}},
            "50to100": {"capacity": 100, "experience": {"trail": 2}},
            "gt100": {"capacity": 170, "experience": {"trail": 2}},
        }),
        ("trail_climb", "experience", "climb", {
            "lt300": {"score": 0, "prefill": {"climb_m": 200}},
            "300to1000": {"score": 1, "prefill": {"climb_m": 600}},
            "1000to2000": {"score": 2, "prefill": {"climb_m": 1400}},
            "gt2000": {"score": 2, "prefill": {"climb_m": 2400}},
        }),
    ],
    "cycling": [
        "LEVEL",
        ("cyc_longest_ride", "capacity", "distance", {
            "lt25": {"capacity": 25, "prefill": {"longest_ride_km": 20}},
            "25to60": {"capacity": 60, "prefill": {"longest_ride_km": 45}},
            "61to120": {"capacity": 120, "prefill": {"longest_ride_km": 95}},
            "121to200": {"capacity": 200, "prefill": {"longest_ride_km": 160}},
            "gt200": {"capacity": 400, "prefill": {"longest_ride_km": 250}},
        }),
        ("cyc_speed", "pace", None, {
            "lt18": {"prefill": {"avg_speed_kmh": 16}},
            "18to22": {"prefill": {"avg_speed_kmh": 20}},
            "23to27": {"prefill": {"avg_speed_kmh": 25}},
            "gt27": {"prefill": {"avg_speed_kmh": 29}},
        }),
    ],
    "swimming": [
        "LEVEL",
        ("swim_nonstop", "capacity", "swim", {
            "lt50": {"capacity": 0.05, "prefill": {"longest_swim_m": 50}},
            "50to400": {"capacity": 0.4, "prefill": {"longest_swim_m": 300}},
            "400to1000": {"capacity": 1.0, "prefill": {"longest_swim_m": 800}},
            "1000to2500": {"capacity": 2.5, "prefill": {"longest_swim_m": 2000}},
            "gt2500": {"capacity": 5.0, "prefill": {"longest_swim_m": 3500}},
        }),
        ("swim_openwater", "experience", "open_water", {
            "none": {"score": 0, "prefill": {"open_water_swims": 0}},
            "some": {"score": 1, "prefill": {"open_water_swims": 2}},
            "raced": {"score": 2, "prefill": {"open_water_swims": 6}},
        }),
    ],
    "triathlon": [
        "LEVEL",
        ("tri_experience", "capacity", "tri_class", {
            "none": {"capacity": 0, "experience": {"open_water": 0}},
            "short": {"capacity": 0},
            "sprint": {"capacity": 1},
            "olympic": {"capacity": 2},
            "long": {"capacity": 3},
        }),
        ("tri_weakest", "weakest", None, {}),
    ],
    "fitness-racing": [
        "LEVEL",
        HYROX_FORMAT,
        ("hyx_5k", "pace", None, {
            "none": {"prefill": {"run_5k_time": "38:00"}},
            "32to40": {"prefill": {"run_5k_time": "35:00"}},
            "26to32": {"prefill": {"run_5k_time": "29:00"}},
            "lt26": {"prefill": {"run_5k_time": "24:00"}},
        }),
    ],
    "ocr": [
        "LEVEL",
        ("ocr_run", "pace", None, {
            "no": {"prefill": {"run_5k_time": "40:00"}},
            "slow": {"prefill": {"run_5k_time": "36:00"}},
            "mid": {"prefill": {"run_5k_time": "30:00"}},
            "fast": {"prefill": {"run_5k_time": "24:00"}},
        }),
        ("ocr_grip", "experience", "grip", {
            "none": {"score": 0, "prefill": {"pull_ups": 0, "dead_hang_s": 10}},
            "hang": {"score": 0, "prefill": {"pull_ups": 0, "dead_hang_s": 30}},
            "some": {"score": 1, "prefill": {"pull_ups": 3, "dead_hang_s": 45}},
            "strong": {"score": 2, "prefill": {"pull_ups": 8, "dead_hang_s": 75}},
        }),
    ],
    "badminton": [
        ("bd_level", "level", None, {
            "learning": {"level": "beginner"},
            "club": {"level": "intermediate"},
            "competitive": {"level": "advanced"},
            "ranked": {"level": "advanced"},
        }),
        ("bd_events", "format", None, {
            "singles": {"formats": ["singles"]},
            "doubles": {"formats": ["doubles", "mixed"]},
            "both": {"formats": []},
        }),
        AGE_QUESTION,
    ],
    "tennis": [
        ("tn_level", "rating", None, {
            "2.5": {"rating": 2.5, "level": "beginner"},
            "3.0": {"rating": 3.0, "level": "intermediate"},
            "3.5": {"rating": 3.5, "level": "intermediate"},
            "4.0": {"rating": 4.0, "level": "advanced"},
            "4.5+": {"rating": 4.5, "level": "advanced"},
        }),
        ("tn_format", "format", None, {
            "singles": {"formats": ["singles"]},
            "doubles": {"formats": ["doubles", "mixed"]},
            "both": {"formats": []},
        }),
        AGE_QUESTION,
    ],
    "pickleball": [
        ("pb_rating", "rating", None, {
            "below_3": {"rating": 2.5, "level": "beginner"},
            "3.0-3.49": {"rating": 3.0, "level": "intermediate"},
            "3.5-3.99": {"rating": 3.5, "level": "intermediate"},
            "4.0-4.49": {"rating": 4.0, "level": "advanced"},
            "4.5+": {"rating": 4.5, "level": "advanced"},
        }),
        ("pb_format", "format", None, {
            "doubles": {"formats": ["doubles"]},
            "mixed": {"formats": ["mixed"]},
            "singles": {"formats": ["singles"]},
        }),
        AGE_QUESTION,
    ],
    "table-tennis": [
        ("tt_level", "level", None, {
            "learning": {"level": "beginner"},
            "club": {"level": "intermediate"},
            "competitive": {"level": "advanced"},
            "ranked": {"level": "advanced"},
        }),
        ("tt_events", "format", None, {
            "singles": {"formats": ["singles"]},
            "doubles": {"formats": ["doubles", "mixed"]},
            "both": {"formats": []},
        }),
        AGE_QUESTION,
    ],
    "squash": [
        ("sq_level", "level", None, {
            "learning": {"level": "beginner"},
            "club": {"level": "intermediate"},
            "competitive": {"level": "advanced"},
            "ranked": {"level": "advanced"},
        }),
        AGE_QUESTION,
        ("sq_tournaments", "experience", "tournaments", {
            "0": {"score": 0},
            "1-2": {"score": 1},
            "3+": {"score": 2},
        }),
    ],
    "football": [
        ("fb_level", "level", None, {
            "casual": {"level": "beginner"},
            "league": {"level": "intermediate"},
            "competitive": {"level": "advanced"},
        }),
        ("fb_format", "format", None, {
            "5-a-side": {"formats": ["5-a-side", "6-a-side"]},
            "7-a-side": {"formats": ["7-a-side"]},
            "11-a-side": {"formats": ["11-a-side"]},
            "any": {"formats": []},
        }),
        ("fb_team", "team", None, {}),
    ],
}

SHORT = {
    "run_longest_recent": "Longest recent run",
    "run_5k_band": "5K time",
    "trail_longest_finish": "Longest trail race",
    "trail_climb": "Biggest climb",
    "cyc_longest_ride": "Longest ride",
    "cyc_speed": "Solo speed",
    "swim_nonstop": "Non-stop swim",
    "swim_openwater": "Open water",
    "tri_experience": "Race history",
    "tri_weakest": "Weakest leg",
    "hyx_5k": "5K time",
    "ocr_run": "Running",
    "ocr_grip": "Grip",
    "bd_level": "Level",
    "bd_events": "Format",
    "tn_level": "Rating",
    "tn_format": "Format",
    "pb_rating": "DUPR",
    "pb_format": "Format",
    "tt_level": "Level",
    "tt_events": "Format",
    "sq_level": "Level",
    "sq_tournaments": "Tournaments",
    "fb_level": "Level",
    "fb_format": "Format",
    "fb_team": "Team",
}

# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def clean(text):
    if not isinstance(text, str):
        return text
    t = text.replace("\u2014", ", ").replace("\u2013", "-").replace("\u00a0", " ")
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s*,", ",", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def deep_clean(obj):
    if isinstance(obj, str):
        return clean(obj)
    if isinstance(obj, list):
        return [deep_clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: deep_clean(v) for k, v in obj.items()}
    return obj


def slugify(text):
    t = text.lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def to_minutes(cut):
    if cut in (None, ""):
        return None
    if isinstance(cut, (int, float)):
        return int(cut)
    m = re.search(r"(\d{1,2}):(\d{2})", str(cut))
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*h", str(cut))
    if m:
        return int(float(m.group(1)) * 60)
    return None


def to_int(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"\d[\d,]*", str(v))
    return int(m.group(0).replace(",", "")) if m else None


def to_float(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def hhmm(v):
    if isinstance(v, str) and re.fullmatch(r"\d{1,2}:\d{2}", v.strip()):
        h, m = v.strip().split(":")
        return f"{int(h):02d}:{m}"
    return None


def parse_offset(label):
    """'T-3 h' -> -180, 'T-90 min' -> -90, 'T-1 day' -> -1440, 'Start'/'T-0' -> 0, 'T+15 min' -> 15."""
    s = str(label).strip().lower()
    if s in ("start", "t-0", "t0", "t+0", "gun", "race start"):
        return 0
    m = re.match(r"t\s*([+-])\s*(\d+(?:\.\d+)?)\s*(day|days|d|h|hr|hrs|hour|hours|min|mins|minutes|m)?", s)
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    n = float(m.group(2))
    unit = m.group(3) or "min"
    mult = 1440 if unit.startswith("d") else 60 if unit.startswith("h") else 1
    return int(sign * n * mult)


def haversine(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))


# --------------------------------------------------------------------------
# builders
# --------------------------------------------------------------------------


def build_cities():
    raw = json.loads((HERE / "cities.json").read_text())
    out = []
    for c in raw["cities"]:
        cl = c.get("climate") or {}
        aq = c.get("air_quality_note")
        sn = c.get("sports_note")
        out.append(
            {
                "slug": c["slug"],
                "name": c["name"],
                "state": c["state"],
                "tier": int(c["tier"]),
                "lat": c["lat"],
                "lon": c["lon"],
                "elevation_m": to_int(c.get("elevation_m")),
                "climate": {
                    "max_c": cl.get("mean_daily_max_c"),
                    "min_c": cl.get("mean_daily_min_c"),
                    "rain_mm": cl.get("mean_monthly_rainfall_mm"),
                    "humidity_pct": cl.get("mean_relative_humidity_pct"),
                    "station": cl.get("station"),
                    "period": cl.get("normals_period"),
                },
                "air_quality_note": clean(aq.get("text") if isinstance(aq, dict) else aq),
                "sports_note": clean(sn.get("text") if isinstance(sn, dict) else sn),
            }
        )
    return out


def level_question(slug, research):
    ld = research.get("level_definitions", {})
    pre = LEVEL_PREFILL.get(slug, {})
    return {
        "id": "level",
        "kind": "level",
        "prompt": LEVEL_PROMPT.get(slug, "How would you describe your level?"),
        "short": "Level",
        "help": None,
        "options": [
            {"value": lvl, "label": lvl.capitalize(), "hint": clean(ld.get(lvl, "")), "level": lvl,
             "prefill": pre.get(lvl, {})}
            for lvl in ("beginner", "intermediate", "advanced")
        ],
    }


def research_question(rq, kind, applies_to, attrs, level_prefill):
    q = {
        "id": rq["id"],
        "kind": kind,
        "prompt": clean(rq.get("question") or rq.get("prompt")),
        "short": SHORT.get(rq["id"]),
        "help": clean(rq.get("help")),
        "options": [],
    }
    if applies_to:
        q["applies_to"] = applies_to
    for o in rq["options"]:
        opt = {"value": str(o["value"]), "label": clean(o["label"]), "hint": clean(o.get("hint"))}
        extra = attrs.get(str(o["value"]), {})
        opt.update(extra)
        if extra.get("level") and level_prefill:
            opt["prefill"] = {**level_prefill.get(extra["level"], {}), **extra.get("prefill", {})}
        q["options"].append(opt)
    missing = set(attrs) - {o["value"] for o in q["options"]}
    if missing:
        raise SystemExit(f"{rq['id']}: attribute keys with no matching option: {missing}")
    return q


def norm_rules(rules):
    out = []
    if isinstance(rules, dict):
        items = rules.items()
    else:
        items = [(r.get("level"), r) for r in rules]
    for lvl, r in items:
        if not isinstance(r, dict):
            continue

        def items_of(key):
            vals = r.get(key) or []
            res = []
            for v in vals:
                if isinstance(v, dict):
                    res.append({"format": clean(v.get("format") or v.get("category") or v.get("draw") or ""),
                                "reason": clean(v.get("reason") or v.get("why") or "")})
                else:
                    res.append({"format": clean(str(v)), "reason": ""})
            return res

        out.append({"level": lvl, "suits": items_of("suits"), "avoid": items_of("avoid")})
    return out


def norm_guide(g):
    def strs(lst):
        res = []
        for x in lst or []:
            if isinstance(x, str):
                res.append(clean(x))
            elif isinstance(x, dict):
                res.append(clean(x.get("text") or x.get("tip") or x.get("principle") or " ".join(map(str, x.values()))))
        return res

    timeline = []
    for step in g.get("event_day_timeline", []):
        label = clean(step.get("t_minus") or step.get("when") or "")
        off = parse_offset(label)
        # steps during or after the event ("T1", "Between games", "Finish") keep their label, no clock time
        timeline.append({"offset_min": off, "label": None if off is not None else label,
                         "what": clean(step.get("step") or step.get("what"))})
    return {
        "kit": [{"item": clean(k["item"]), "why": clean(k.get("why"))} for k in g.get("kit_checklist", [])],
        "timeline": timeline,
        "nutrition": strs(g.get("nutrition_hydration")),
        "safety": strs(g.get("safety")),
        "beginner_tips": strs(g.get("beginner_tips")),
        "training": strs(g.get("training_principles")),
        "glossary": [
            {"term": clean(x["term"]), "meaning": clean(x.get("definition") or x.get("meaning"))}
            for x in g.get("glossary", [])
        ],
    }


def build_sports():
    research = {}
    for f in ("content-endurance.json", "content-court.json"):
        for s in json.loads((HERE / f).read_text())["sports"]:
            research[s["slug"]] = s
    out = []
    for order, (slug, name, family, color) in enumerate(SPORTS, start=1):
        r = research[slug]
        level_prefill = LEVEL_PREFILL.get("court" if family == "court" else slug)
        rq_by_id = {q["id"]: q for q in r["profile_questions"]}
        questions = []
        for spec in QUESTIONS[slug]:
            if spec == "LEVEL":
                questions.append(level_question(slug, r))
            elif isinstance(spec, dict):
                questions.append(spec)
            else:
                qid, kind, applies_to, attrs = spec
                questions.append(research_question(rq_by_id[qid], kind, applies_to, attrs, level_prefill))
        out.append(
            deep_clean(
                {
                    "slug": slug,
                    "name": name,
                    "family": family,
                    "color": color,
                    "sort_order": order,
                    "tagline": r["tagline"],
                    "description": r["description"],
                    "disciplines": r.get("disciplines", []),
                    "questions": questions,
                    "level_definitions": r.get("level_definitions", {}),
                    "recommendation_rules": norm_rules(r.get("recommendation_rules", {})),
                    "guide": norm_guide(r.get("guide", {})),
                    "sources": r.get("sources", []),
                }
            )
        )
    return out


LEVELS = {"beginner", "intermediate", "advanced", "open"}


def build_events(cities):
    by_name = {c["name"].lower(): c for c in cities}
    by_slug = {c["slug"]: c for c in cities}
    events = []
    seen = Counter()
    warnings = []
    for f in EVENT_FILES:
        for e in json.loads((HERE / f).read_text())["events"]:
            if e["sport"] in DROPPED_SPORTS:
                continue
            city = by_name.get(e["city"].lower()) or by_slug.get(slugify(e["city"]))
            if city is None:
                raise SystemExit(f"unknown city {e['city']!r} for {e['name']}")
            year = e["start_date"][:4]
            base = slugify(re.sub(r"\b20\d\d\b", "", e["name"]))
            slug = f"{base}-{year}"
            seen[slug] += 1
            if seen[slug] > 1:
                slug = f"{base}-{city['slug']}-{year}"
            lat, lon = to_float(e.get("venue_lat")), to_float(e.get("venue_lon"))
            if lat is None or lon is None or not (6 <= lat <= 37 and 68 <= lon <= 98):
                lat, lon = None, None
            elif haversine(lat, lon, city["lat"], city["lon"]) > 450:
                warnings.append(f"{slug}: venue {haversine(lat, lon, city['lat'], city['lon']):.0f} km from hub")
            reg = e.get("registration") or {}
            cats = []
            names = set()
            for c in e.get("categories", []):
                nm = clean(c["name"])
                if nm in names:
                    nm = f"{nm} ({len(names) + 1})"
                names.add(nm)
                swim, bike, run = to_float(c.get("swim_km")), to_float(c.get("bike_km")), to_float(c.get("run_km"))
                dist = to_float(c.get("distance_km"))
                if dist is None and any((swim, bike, run)):
                    dist = round(sum(x or 0 for x in (swim, bike, run)), 2)
                lvl = (c.get("level") or "open").lower()
                cats.append(
                    {
                        "name": nm,
                        "distance_km": dist,
                        "swim_km": swim,
                        "bike_km": bike,
                        "run_km": run,
                        "fee_inr": to_int(c.get("fee_inr")),
                        "start_time": hhmm(c.get("start_time")),
                        "cutoff_minutes": to_minutes(c.get("cutoff")),
                        "min_age": to_int(c.get("min_age")),
                        "level": lvl if lvl in LEVELS else "open",
                        "eligibility": clean(c.get("eligibility")),
                        "notes": clean(c.get("notes")),
                    }
                )
            course = e.get("course") or {}
            events.append(
                deep_clean(
                    {
                        "slug": slug,
                        "name": re.sub(r"\s+20\d\d$", "", e["name"]).strip(),
                        "edition": e.get("edition"),
                        "sport": e["sport"],
                        "discipline": e.get("discipline"),
                        "city": city["slug"],
                        "venue": e.get("venue"),
                        "lat": lat,
                        "lon": lon,
                        "start_date": e["start_date"],
                        "end_date": e.get("end_date") or e["start_date"],
                        "date_status": e.get("date_status") if e.get("date_status") in ("confirmed", "expected")
                        else "expected",
                        "last_edition_date": e.get("last_edition_date"),
                        "organiser": e.get("organiser"),
                        "official_url": e.get("official_url"),
                        "registration_status": reg.get("status")
                        if reg.get("status") in ("open", "closed", "upcoming", "unknown")
                        else "unknown",
                        "registration_opens": reg.get("opens"),
                        "registration_closes": reg.get("closes"),
                        "registration_url": reg.get("url"),
                        "registration_notes": reg.get("notes"),
                        "summary": e.get("summary") or "",
                        "categories": cats,
                        "course": {
                            "terrain": course.get("terrain"),
                            "surface": course.get("surface"),
                            "elevation_gain_m": to_int(course.get("elevation_gain_m")),
                            "profile": course.get("profile"),
                            "description": course.get("description"),
                        },
                        "format": e.get("format"),
                        "highlights": e.get("highlights") or [],
                        "tips": e.get("tips") or [],
                        "amenities": e.get("amenities") or [],
                        "beginner_friendly": bool(e.get("beginner_friendly")),
                        "tags": e.get("tags") or [],
                        "sources": e.get("sources") or [],
                    }
                )
            )
    return events, warnings


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "events").mkdir(exist_ok=True)
    cities = build_cities()
    sports = build_sports()
    events, warnings = build_events(cities)
    (OUT / "cities.json").write_text(json.dumps({"cities": cities}, indent=1, ensure_ascii=False) + "\n")
    (OUT / "sports.json").write_text(json.dumps({"sports": sports}, indent=1, ensure_ascii=False) + "\n")
    by_sport = {}
    for e in events:
        by_sport.setdefault(e["sport"], []).append(e)
    for old in (OUT / "events").glob("*.json"):
        old.unlink()
    for sport, evs in by_sport.items():
        evs.sort(key=lambda e: (e["start_date"], e["name"]))
        (OUT / "events" / f"{sport}.json").write_text(json.dumps({"events": evs}, indent=1, ensure_ascii=False) + "\n")
    for w in warnings:
        print("  ~", w)
    print(f"cities {len(cities)}, sports {len(sports)}, events {len(events)}")
    print("by sport:", dict(sorted(Counter(e["sport"] for e in events).items(), key=lambda kv: -kv[1])))


if __name__ == "__main__":
    main()
