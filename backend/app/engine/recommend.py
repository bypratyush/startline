"""Content-based event recommendations.

For an athlete with a profile in the event's sport, every category of the event
is scored for fit (level, distance capacity, format, age and rating brackets,
equipment). The best category is then combined with event-level signals:

    score = 100 x (0.50 fit + 0.25 proximity + 0.15 preparation time + 0.10 registration)

Each signal contributes a short, human-readable reason so the UI can explain
why an event was recommended. Nothing is learned from other users: the result is
deterministic and easy to test.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from .categories import (
    age_bracket,
    category_formats,
    level_index,
    primary_distance,
    rating_bracket,
    tri_class,
)
from .geo import haversine_km
from .profile import SportProfile

WEIGHTS = {"fit": 0.50, "proximity": 0.25, "timing": 0.15, "registration": 0.10}
RECOMMEND_THRESHOLD = 70
PARA = re.compile(r"wheelchair|\bpara\b|divyang|visually impaired|blind", re.I)
TRI_CLASS_NAMES = ["aquathlon or super-sprint", "sprint", "olympic", "70.3", "full distance"]
LEVEL_WORDS = {0: "beginner", 1: "intermediate", 2: "advanced"}


@dataclass
class CategoryFit:
    category_id: int
    category_name: str
    fit: float
    eligible: bool = True
    reasons: list[str] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)


@dataclass
class Match:
    score: int
    tier: str
    category_id: int
    category_name: str
    reasons: list[str]
    cautions: list[str]
    distance_km: float | None

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "tier": self.tier,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "reasons": self.reasons,
            "cautions": self.cautions,
        }


def _fmt_km(km: float) -> str:
    if km < 1:
        return f"{int(round(km * 1000))} m"
    return f"{km:.1f}".rstrip("0").rstrip(".") + " km"


def _ratio_fit(need: float, cap: float, unit_word: str, cap_label: str | None = None):
    r = need / cap if cap else 99
    # quote the user's own answer when it is a range like "11-21 km"
    have = f" ({cap_label.lower()})" if cap_label and any(ch.isdigit() for ch in cap_label) else ""
    if r <= 1.0:
        return 1.0, f"{_fmt_km(need)} is within your {unit_word}{have}", None
    if r <= 1.35:
        return 0.8, f"A reachable step up from your {unit_word}{have}", None
    if r <= 2.0:
        return 0.45, None, f"About {r:.1f}x your current {unit_word}: needs a proper build-up"
    if r <= 3.0:
        return 0.2, None, f"Roughly {r:.0f}x your current {unit_word}"
    return 0.05, None, f"Far beyond your current {unit_word}"


def category_fit(event, cat, p: SportProfile) -> CategoryFit:
    family = event.sport.family
    out = CategoryFit(category_id=cat.id, category_name=cat.name, fit=0.0)

    # ---- hard eligibility: age brackets and rating caps --------------------
    lo, hi = age_bracket(cat)
    if p.age is not None:
        if hi is not None and p.age >= hi:
            out.eligible = False
            out.cautions.append(f"Age group is under {hi}")
        if lo is not None and lo >= 30 and p.age < lo:
            out.eligible = False
            out.cautions.append(f"Open to {lo}+ only")
    elif hi is not None and hi <= 18:
        # junior and kids categories: profiles are adults unless they say otherwise
        out.eligible = False
    if PARA.search(cat.name):
        # para-sport draws: the profile does not ask, so never push them as a default pick
        out.eligible = False
    rb = rating_bracket(cat) if family == "court" else None
    if rb and p.rating is not None:
        r, plus = rb
        if not plus and p.rating > r + 0.01:
            out.eligible = False
            out.cautions.append(f"Capped at {r}; your rating is {p.rating}")

    # ---- level ----------------------------------------------------------------
    if rb and p.rating is not None:
        r, plus = rb
        diff = r - p.rating
        if abs(diff) < 0.01 or (plus and p.rating >= r):
            lf = 1.0
            out.reasons.append(f"{r} draw matches your {p.rating} rating")
        elif 0 < diff <= 0.5:
            lf = 0.6
            out.reasons.append(f"A half-point step up from your {p.rating}")
        elif diff > 0.5:
            lf = 0.15
        else:
            lf = 0.3
    else:
        ci = level_index(cat.level, family)
        if ci is None:
            lf = 0.75
        else:
            d = ci - p.level_idx
            lf = {0: 1.0, 1: 0.55, -1: 0.7, 2: 0.12, -2: 0.3}[d]
            if d == 0:
                out.reasons.append(f"Pitched at {LEVEL_WORDS[ci]} level, like you")
            elif d == -1:
                out.reasons.append("Comfortable for your level")
            elif d == 1:
                out.cautions.append("A step above your current level")
            elif d == 2:
                out.cautions.append("Built for advanced athletes")

    # ---- capacity: distance, triathlon class --------------------------------
    cf = None
    if family in ("run", "ride", "swim"):
        need = primary_distance(cat, family)
        key = "swim" if family == "swim" else "distance"
        cap = p.capacity.get(key)
        if need and cap:
            word = {"run": "longest run", "ride": "longest ride", "swim": "non-stop swim"}[family]
            if event.sport.slug == "trail-running":
                word = "longest trail race"
            cf, reason, caution = _ratio_fit(need, cap, word, p.capacity_label.get(key))
            if p.level_idx == 2 and need / cap < 0.35:
                cf, reason = 0.6, "Short for you: a good speed test"
            if reason:
                out.reasons.append(reason)
            if caution:
                out.cautions.append(caution)
    elif family == "tri":
        done = p.capacity.get("tri_class")
        c = tri_class(cat)
        if event.discipline == "duathlon":
            c = min(c, 2)
        if done is not None:
            d = c - int(done)
            if d <= 0 and int(done) == 0:
                cf = 1.0
                out.reasons.append("A short first race: the right place to start")
            elif d <= 0:
                cf = 1.0
                out.reasons.append(f"You have raced {TRI_CLASS_NAMES[c]} distance or longer")
            elif d == 1:
                cf = 0.85
                out.reasons.append(f"The natural next step: {TRI_CLASS_NAMES[c]}")
            elif d == 2:
                cf = 0.35
                out.cautions.append(f"Two steps up to {TRI_CLASS_NAMES[c]}")
            else:
                cf = 0.05
                out.cautions.append(f"{TRI_CLASS_NAMES[c].capitalize()} is far beyond your race history")
        if p.weakest == "swim":
            if event.discipline == "duathlon":
                cf = min(1.0, (cf or 0.8) + 0.1)
                out.reasons.append("No swim leg: plays to your strengths")
            elif cat.swim_km and cat.swim_km >= 1.5:
                out.cautions.append(f"{_fmt_km(cat.swim_km)} swim: your weakest leg")

    # ---- open-water and trail experience ------------------------------------
    terrain = (event.course or {}).get("terrain")
    if family in ("swim", "tri") and terrain in ("open-water", "mixed", None) and event.discipline != "duathlon":
        ow = p.experience.get("open_water")
        if ow == 0 and (family == "swim" and terrain == "open-water" or family == "tri"):
            out.cautions.append("Practise a supervised open-water swim first")
            lf *= 0.9
    if family == "run" and event.sport.slug == "trail-running":
        tx = p.experience.get("trail")
        if tx == 0 and (level_index(cat.level, family) or 0) >= 1:
            out.cautions.append("Technical trail: get a few off-road runs in first")
            lf *= 0.75

    # ---- format, equipment ----------------------------------------------------
    fmts = category_formats(cat)
    mult = 1.0
    if p.formats and fmts:
        if fmts & p.formats:
            pretty = sorted(fmts & p.formats)[0]
            out.reasons.append(f"Your preferred format: {pretty}")
        else:
            mult *= 0.55
            out.cautions.append(f"Format is {', '.join(sorted(fmts))}")
    if family == "ride" and p.disciplines and event.discipline and event.discipline not in p.disciplines:
        mult *= 0.5
        out.cautions.append("Needs a different bike type" if event.discipline != "mtb" else "Needs a mountain bike")

    # ---- age-group bonus --------------------------------------------------------
    if p.age is not None and lo is not None and lo >= 30 and p.age >= lo:
        out.reasons.append(f"Fits your {lo}+ age group")

    out.fit = (0.5 * lf + 0.5 * cf if cf is not None else lf) * mult
    if not out.eligible:
        out.fit *= 0.1
    return out


def prep_weeks(family: str, cat, level_idx: int, sport_slug: str = "") -> float:
    """Typical build-up an athlete of this level wants before this category."""
    d = cat.distance_km or 0
    if family == "run":
        base = 6 if d <= 5 else 8 if d <= 10 else 12 if d <= 21.1 else 16 if d <= 42.2 else 20
        if sport_slug == "trail-running":
            base += 2
    elif family == "ride":
        base = 4 if d <= 50 else 8 if d <= 100 else 10 if d <= 200 else 14 if d <= 400 else 18
    elif family == "swim":
        s = cat.swim_km or d
        base = 6 if s <= 1.5 else 10 if s <= 5 else 14
    elif family == "tri":
        base = [8, 10, 14, 20, 30][tri_class(cat)]
    elif family == "hyrox":
        base = 8
    elif family == "ocr":
        base = 6
    else:
        base = 3
    return base * {0: 1.25, 1: 1.0, 2: 0.6}[level_idx]


def score_event(event, profile: SportProfile | None, city, today: date) -> Match | None:
    if profile is None or not event.categories:
        return None
    fits = [category_fit(event, c, profile) for c in event.categories]
    best = max(fits, key=lambda f: (f.eligible, f.fit))
    cat = next(c for c in event.categories if c.id == best.category_id)
    reasons = list(best.reasons)
    cautions = list(best.cautions)

    # proximity
    dist = None
    if city is not None:
        dist = haversine_km(city.lat, city.lon, event.lat, event.lon)
        if dist <= 40:
            prox = 1.0
            reasons.append(f"In {city.name}")
        elif dist <= 150:
            prox = 0.85
            reasons.append(f"{int(round(dist, -1))} km from {city.name}")
        elif dist <= 400:
            prox = 0.55
            reasons.append("Worth a weekend trip")
        elif dist <= 900:
            prox = 0.35
        else:
            prox = 0.25
    else:
        prox = 0.7

    # preparation time
    weeks = (event.start_date - today).days / 7
    need = prep_weeks(event.sport.family, cat, profile.level_idx, event.sport.slug)
    if weeks >= need:
        timing = 1.0 if weeks <= 40 else 0.85
        if weeks <= 30:
            reasons.append(f"{int(weeks)} week{'s' if int(weeks) != 1 else ''} to prepare")
    else:
        timing = 0.25 + 0.75 * max(weeks, 0) / need
        w = max(int(weeks), 0)
        cautions.append(f"Only {w} week{'s' if w != 1 else ''} away: tight for a full build-up")

    # registration
    status = event.registration_status
    if status == "open":
        reg = 1.0
        reasons.append("Registration open")
    elif status == "upcoming":
        reg = 0.85
    elif status == "closed":
        reg = 0.3
        cautions.append("Registration closed")
    else:
        reg = 0.75

    score = 100 * (
        WEIGHTS["fit"] * best.fit
        + WEIGHTS["proximity"] * prox
        + WEIGHTS["timing"] * timing
        + WEIGHTS["registration"] * reg
    )
    if event.beginner_friendly and profile.level_idx == 0:
        score += 3
        reasons.append("Beginner friendly")
    score = int(round(max(0, min(100, score))))
    tier = "great" if score >= 78 else "good" if score >= 62 else "stretch"

    # keep the explanation short: the strongest three reasons, two cautions
    return Match(
        score=score,
        tier=tier,
        category_id=best.category_id,
        category_name=best.category_name,
        reasons=_dedupe(reasons)[:3],
        cautions=_dedupe(cautions)[:2],
        distance_km=dist,
    )


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
