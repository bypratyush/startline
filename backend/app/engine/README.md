# How StartLine decides

> **Submitted by:** Pratyush Mohanty  |  **Roll No.:** 24BCS10238

Everything in this folder is plain, deterministic Python. The same profile and
event always give the same answer, so every rule below is covered by
`backend/tests/test_engine.py`.

## 1. Profiling (`profile.py`)

Each sport asks 2 or 3 required single-choice questions (`app/seed/data/sports.json`).
The wording, options and hints came from the sport-content research in
`research/content-*.json`. Every option carries machine-readable attributes,
so nothing is parsed from labels at runtime:

| Question kind | Attribute | Example |
|---|---|---|
| `level` | `level` | Swimming "Beginner: swims under 400 m without stopping" |
| `capacity` | `capacity` (km or triathlon class) | "How far can you swim non-stop?" 400 m-1 km -> 1.0 |
| `experience` | `score` 0-2 | Open water: none / some / raced |
| `format` | `formats` | Pickleball: doubles, mixed, singles |
| `rating` | `rating` + `level` | DUPR 3.5-3.99 -> 3.5, intermediate |
| `age` | `age` | 45 to 54 -> eligible for 35+ and 45+ draws |
| `weakest` | value | Triathlon weakest leg: swim |

Options can also carry `prefill` values. These are the readiness calculator's
defaults, so a profiled athlete starts with sensible numbers.

## 2. Recommendations (`recommend.py`)

For every category of an event in one of the athlete's sports:

* **Hard rules** first. Categories become ineligible for age brackets the athlete
  is outside (`45+`, `U-19`, `ages 8-10`, kids runs), rated draws capped below
  their rating, and para-sport draws.
* **Level fit**: same level 1.0, one easier 0.7, one harder 0.55, two harder 0.12.
* **Capacity fit**: the race distance divided by what the athlete said they can do.
  A ratio up to 1.0 scores 1.0, up to 1.35 scores 0.8 ("a reachable step up"),
  up to 2.0 scores 0.45, and beyond that it drops off. Triathlon compares
  distance classes (super-sprint, sprint, olympic, 70.3, full): the next class
  up is "the natural next step".
* **Format, equipment, open-water and trail experience** adjust the fit, and
  each adjustment adds a reason or a caution.

The best category is then combined with event-level signals:

```
score = 100 x (0.50 fit + 0.25 proximity + 0.15 preparation time + 0.10 registration open)
```

* **Proximity** (haversine distance from the athlete's city): within 40 km 1.0,
  150 km 0.85, 400 km 0.55, 900 km 0.35, beyond that 0.25.
* **Preparation time**: weeks left against a typical build-up for that distance
  and level (for example a half marathon is 12 weeks, x1.25 for a beginner and
  x0.6 for an advanced athlete).

Events scoring 70 or more are "Picked for you". With recommendations switched
off (`PATCH /api/athletes/{id}`), the list is plain date order with no scores.

## 3. Readiness (`readiness.py`)

| Family | Prediction | Main components (weights) |
|---|---|---|
| Road running | Riegel: T2 = T1 x (D2/D1)^1.06, exponent raised by up to 0.04 at half marathon and beyond when weekly volume is low | long run 35, weekly volume 25, time to build 20, cutoff margin 20 |
| Trail | Riegel on ITRA effort distance (km + D+/100) x 1.10 for terrain | as above plus climbing 15 |
| Cycling | average speed x course-profile factor, +18% stop time on brevets | long ride 35, weekly km 20, runway 20, time limit 25, climbing 15 |
| Swimming | pool pace x 1.06 lake/river, 1.12 sea | non-stop distance 35, open-water practice 20, cutoff 20, frequency 15, runway 15 |
| Triathlon | swim + bike + run off the bike (+4% to +20% by distance) + transitions | swim, bike, run 25 each, runway 15, cutoff 20 |
| HYROX | 8 x 1 km at 1.22 x 5K pace (compromised running) + station time by experience + Roxzone | running 30, stations 30, wall balls 15, frequency 10, runway 15 |
| OCR | Riegel run x 1.25 + about a minute per obstacle, scaled by grip and pulling | running 30, pulling 20-25, grip 20-25, frequency 10, runway 20 |
| Racquet | none (match play) | draw fit 35, match practice 25, tournament-day stamina 20, training 10, runway 10 |
| Football | none | squad size 25, level 25, match fitness 20, playing together 20, runway 10 |

Verdicts: 80+ **Race ready**, 60-79 **Nearly there**, 40-59 **Build first**,
below 40 **Not this one yet**.

The training runway builds the long session by about 10% a week (at least
1.5 km for runs, 10 km for rides), with an easier week every fourth week and a
taper of 1 to 3 weeks before race day.

Key constants and where they come from:

* Riegel exponent 1.06: Riegel's endurance model, as used by most race calculators (runnersconnect.net/race-calculators).
* Long-run targets of 16 km for a half and 32 km for a marathon: the peaks of Hal Higdon's novice plans (halhigdon.com).
* ITRA effort distance = km + D+/100 (run-motion.com, ITRA km-effort).
* Brevet time limits: 200 km 13:30, 300 km 20:00, 400 km 27:00, 600 km 40:00, 1000 km 75:00, 1200 km 90:00 (Audax Club Parisien BRM rules; Audax India Randonneurs).
* IRONMAN 70.3 swim 1:10, swim plus bike 5:30, finish 8:30; full distance swim 2:20, finish 17:00.
* HYROX medians: Open men about 1:28, Open women about 1:36 (Boxlife analysis of 700,000 results). Compromised running adds 15-20 s/km over open pace.
* Typical tournament-day load per racquet sport, marked "StartLine estimate" in `research/content-court.json`, because no federation publishes it.

Factors the research could not source directly (open-water slowdown, terrain
factor, station minutes) are labelled "StartLine heuristic" in the research
files, and the UI calls every prediction an estimate.

## 4. Event guide (`guide.py`)

* **Weather card.** It uses the host city's IMD climate normals for the event
  month. The temperature at the start time is interpolated between the daily
  low and high. It is then turned into a heat index with the US National
  Weather Service Rothfusz regression, and placed in an NWS band: caution 27°C,
  extreme caution 32°C, danger 39°C, extreme danger 52°C. From October to
  February the card also shows the city's CPCB air-quality note.
* **Race-day timeline.** The sport's timeline steps are anchored to the chosen
  category's real start time, so "T-90 min" becomes "03:30" for a 05:00 gun.

## 5. Season planner (`season.py`)

Registered and saved events are sorted by date. A warning appears when two sit
closer together than the recovery time after the first one. For running this
is the classic "one easy day per mile raced" (0.62 days per km of effort
distance). Triathlon uses 5 to 42 days by distance class, and court and team
sports use 2 days.
