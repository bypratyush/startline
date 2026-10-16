"""Turn a user's answers to a sport's 2-3 profile questions into a usable profile.

Each sport's questions live in the sports table (seeded from
app/seed/data/sports.json). Every question has a `kind` and every option can
carry machine-readable attributes, so the recommender never has to parse labels:

    level       option.level            beginner | intermediate | advanced
    capacity    option.capacity         km (or triathlon distance class), question.applies_to
    experience  option.score            0 none, 1 some, 2 regular, question.applies_to
    format      option.formats          e.g. ["doubles", "mixed"]; empty means any
    age         option.age              representative age for the bracket
    rating      option.rating           DUPR / NTRP style number, plus option.level
    equipment   option.disciplines      event disciplines that bike can ride
    weakest     option.value            swim | bike | run
    team        option.value            full | partial | none

Any option may also carry `prefill`, a dict of readiness-calculator defaults.
"""

from dataclasses import dataclass, field

from .categories import LEVEL_INDEX


class ProfileError(ValueError):
    pass


@dataclass
class SportProfile:
    sport_slug: str
    family: str
    level: str
    capacity: dict[str, float] = field(default_factory=dict)
    capacity_label: dict[str, str] = field(default_factory=dict)
    experience: dict[str, int] = field(default_factory=dict)
    formats: set[str] | None = None
    age: int | None = None
    rating: float | None = None
    disciplines: set[str] | None = None
    weakest: str | None = None
    team: str | None = None
    prefill: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)

    @property
    def level_idx(self) -> int:
        return LEVEL_INDEX.get(self.level, 1)


def _option(question: dict, value) -> dict | None:
    for opt in question.get("options", []):
        if opt["value"] == value:
            return opt
    return None


def validate_answers(sport, answers: dict) -> dict:
    """Every question is required and must use one of its option values."""
    clean = {}
    for q in sport.questions:
        value = answers.get(q["id"])
        if value is None or value == "":
            raise ProfileError(f"{sport.name}: please answer '{q['prompt']}'")
        if _option(q, value) is None:
            raise ProfileError(f"{sport.name}: '{value}' is not a valid answer to '{q['prompt']}'")
        clean[q["id"]] = value
    return clean


def build_profile(sport, answers: dict) -> SportProfile:
    level = None
    p = SportProfile(sport_slug=sport.slug, family=sport.family, level="intermediate")
    for q in sport.questions:
        opt = _option(q, answers.get(q["id"]))
        if opt is None:
            continue
        p.labels[q["id"]] = opt["label"]
        p.prefill.update(opt.get("prefill") or {})
        kind = q.get("kind")
        if level is None and opt.get("level"):
            level = opt["level"]
        for key, val in (opt.get("experience") or {}).items():
            p.experience[key] = int(val)
        if kind == "capacity" and opt.get("capacity") is not None:
            p.capacity[q.get("applies_to", "distance")] = float(opt["capacity"])
            p.capacity_label[q.get("applies_to", "distance")] = opt["label"]
        elif kind == "experience":
            p.experience[q.get("applies_to", "general")] = int(opt.get("score", 0))
        elif kind == "format":
            fmts = opt.get("formats") or []
            p.formats = set(fmts) if fmts else None
        elif kind == "age":
            p.age = opt.get("age")
        elif kind == "rating":
            p.rating = opt.get("rating")
        elif kind == "equipment":
            d = opt.get("disciplines") or []
            p.disciplines = set(d) if d else None
        elif kind == "weakest":
            p.weakest = opt["value"]
        elif kind == "team":
            p.team = opt["value"]
    if level:
        p.level = level
    return p


def derive_level(sport, answers: dict) -> str:
    return build_profile(sport, answers).level
