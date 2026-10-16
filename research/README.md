# Research data

> **Submitted by:** Pratyush Mohanty  |  **Roll No.:** 24BCS10238

These are the raw files from the research, kept exactly as collected, with a
source URL on every event. `build_seed.py` turns them into the app's seed
catalogue in `backend/app/seed/data/`.

| File | Contents |
|---|---|
| `EVENT_SCHEMA.md` | the brief and JSON schema every event follows |
| `running-tier1.json` | 51 road races in the 8 Tier 1 cities |
| `running-tier2-trail.json` | 25 road races in Tier 2 cities, 16 trail and ultra races |
| `tri-swim.json` | 21 triathlons, duathlons and aquathlons, 15 open-water and pool swims |
| `cycling-fitness-ocr.json` | 18 brevets and cycling events, 9 HYROX and fitness races, 9 Devils Circuit legs |
| `racquet.json` | 13 tennis, 11 badminton and 9 pickleball tournaments |
| `team-other.json` | football, table tennis and squash events (plus one basketball event that was dropped) |
| `content-endurance.json`, `content-court.json` | per sport: profile questions, level definitions, recommendation rules, readiness constants with sources, kit, race-day timeline, nutrition, safety, tips, glossary |
| `cities.json` | 36 hub cities: coordinates, tier, IMD climate normals by month, CPCB air-quality note |

```bash
python3 research/build_seed.py      # rebuild backend/app/seed/data
cd backend && python -m app.seed --check
```

Rules followed: only events found on the web, with a source that was actually
opened; unknown values left empty, never guessed; unpublished 2026-27 dates
marked "expected", with the previous edition's date.
