"""Helpers that read meaning out of an event category.

Categories come from real event listings, so their names are free text
("Mixed Doubles 3.5", "Men's Singles 45+", "Olympic Distance"). These helpers
pull out the parts the recommender and the readiness calculator need.
"""

import re
from functools import lru_cache

LEVELS = ("beginner", "intermediate", "advanced")
LEVEL_INDEX = {name: i for i, name in enumerate(LEVELS)}


def level_index(level: str | None, family: str) -> int | None:
    """beginner=0, intermediate=1, advanced=2. "open" depends on the sport.

    In endurance events "open" means anyone can enter (None = no level signal).
    In court and team sports an "Open" draw is the top draw, so it counts as advanced.
    """
    if level in LEVEL_INDEX:
        return LEVEL_INDEX[level]
    if family in ("court", "team"):
        return 2
    return None


def tri_class(cat) -> int:
    """0 aquathlon/duathlon/super-sprint, 1 sprint, 2 olympic, 3 70.3, 4 full distance."""
    total = cat.distance_km or sum(x or 0 for x in (cat.swim_km, cat.bike_km, cat.run_km))
    if not total:
        return 1
    if total < 22:
        return 0
    if total < 40:
        return 1
    if total < 80:
        return 2
    if total < 170:
        return 3
    return 4


def primary_distance(cat, family: str) -> float | None:
    if family == "swim":
        return cat.swim_km or cat.distance_km
    return cat.distance_km


_AGE_PLUS = re.compile(r"(?<![\d.])(\d{2})\s*(?:\+|plus|and above|& above|years and above)", re.I)
_AGE_UNDER = re.compile(r"\b(?:u|under)[\s-]?(\d{2})\b", re.I)
_KIDS = re.compile(r"\b(kids?|children|child|junior|juniors|tiny tots)\b", re.I)
_AGE_SPAN = re.compile(r"\bages?\s*(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\b", re.I)
_RATING = re.compile(r"(?<![\d])([2-5]\.[05])(\s*\+)?")


def age_bracket(cat) -> tuple[int | None, int | None]:
    """Return (min_age, max_age) implied by the category name and min_age."""
    return _age_bracket(cat.name, cat.min_age)


@lru_cache(maxsize=4096)
def _age_bracket(name: str, min_age: int | None) -> tuple[int | None, int | None]:
    lo = min_age
    hi = None
    # Only the category name and min_age are trusted: eligibility text often mentions
    # several age slabs ("youth 15-21 and 65+ criteria") that are not the entry rule.
    m = _AGE_PLUS.search(name)
    if m:
        lo = max(lo or 0, int(m.group(1)))
    m = _AGE_UNDER.search(name)
    if m:
        hi = int(m.group(1))
    m = _AGE_SPAN.search(name)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2)) + 1
    if hi is None and _KIDS.search(name):
        hi = 16
    return lo, hi


def rating_bracket(cat) -> tuple[float, bool] | None:
    """(rating, is_plus) for skill-rated draws like "Mixed Doubles 3.5" or "4.0+"."""
    return _rating_bracket(cat.name)


@lru_cache(maxsize=4096)
def _rating_bracket(name: str) -> tuple[float, bool] | None:
    m = _RATING.search(name)
    if not m:
        return None
    return float(m.group(1)), bool(m.group(2))


FORMAT_WORDS = {
    "singles": ("singles",),
    "doubles": ("doubles",),
    "mixed": ("mixed",),
    "5-a-side": ("5-a-side", "5 a side", "five-a-side", "5s", "futsal", "5v5"),
    "6-a-side": ("6-a-side", "6 a side", "6s"),
    "7-a-side": ("7-a-side", "7 a side", "7s", "sevens"),
    "11-a-side": ("11-a-side", "11 a side", "full-field", "full field"),
    "3x3": ("3x3", "3 x 3", "3-on-3", "3 on 3"),
    "5v5": ("5v5", "5 on 5", "5-on-5"),
    "solo": ("solo", "individual", "open men", "open women", "pro men", "pro women", "open division", "pro division"),
    "pair": ("pair",),
    "relay": ("relay", "team of 4", "teams of 4", "team relay"),
}


def category_formats(cat) -> set[str]:
    return set(_category_formats(cat.name))


@lru_cache(maxsize=4096)
def _category_formats(raw: str) -> frozenset[str]:
    name = f" {raw.lower()} "
    found = {fmt for fmt, words in FORMAT_WORDS.items() if any(w in name for w in words)}
    if "mixed" in found and "doubles" not in name.replace("mixed doubles", " "):
        # "Mixed Doubles" alone is a mixed draw, not a men's or women's doubles draw
        found.discard("doubles")
    return frozenset(found)


def is_doubles(cat) -> bool:
    return bool(category_formats(cat) & {"doubles", "mixed", "pair"})


def is_team_entry(cat, family: str) -> bool:
    return family == "team" or bool(category_formats(cat) & {"relay"})


def format_seconds(seconds: float | None) -> str | None:
    if seconds is None:
        return None
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def parse_duration(text: str | None) -> int | None:
    """'25:30' -> 1530 s, '1:58:20' -> 7100 s, '7:00' (h:mm cutoffs are handled elsewhere)."""
    if not text:
        return None
    parts = str(text).strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    if len(nums) == 1:
        return nums[0] * 60
    return None
