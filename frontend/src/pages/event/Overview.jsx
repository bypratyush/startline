import { ArrowRight, Check, Mountains, Sparkle, Thermometer, Warning } from "@phosphor-icons/react";
import { Link } from "react-router";
import { Badge, MatchPill } from "../../components/ui.jsx";
import { formatDate, inr, km, LEVEL_LABEL, minutesLabel, sentenceCase, TERRAIN_LABEL, weeksLabel } from "../../lib/format.js";
import { WeatherBand } from "./Guide.jsx";

function CategoryTable({ event, categoryId, setCategory, matchId }) {
  const fam = event.sport.family;
  const multisport = fam === "tri";
  const court = fam === "court" || fam === "team";
  return (
    <div className="cat-table" role="table" aria-label="Categories">
      <div className="ct-row ct-head" role="row">
        <span role="columnheader">Category</span>
        {!court ? <span role="columnheader">{multisport ? "Swim · Bike · Run" : "Distance"}</span> : null}
        <span role="columnheader">Start</span>
        {!court ? <span role="columnheader">Cutoff</span> : null}
        <span role="columnheader">Level</span>
        <span role="columnheader" className="ct-fee">
          Entry
        </span>
      </div>
      {event.categories.map((c) => (
        <button
          type="button"
          role="row"
          key={c.id}
          className={`ct-row${c.id === categoryId ? " on" : ""}`}
          onClick={() => setCategory(c.id)}
          title="Use this category for readiness and registration"
        >
          <span role="cell" className="ct-name">
            <span className="ct-radio" aria-hidden="true" />
            <span>
              {c.name}
              {c.id === matchId ? (
                <Badge tone="accent">
                  <Sparkle size={11} weight="fill" /> Your match
                </Badge>
              ) : null}
              {c.eligibility ? <span className="ct-elig">{c.eligibility}</span> : null}
            </span>
          </span>
          {!court ? (
            <span role="cell" className="num">
              {multisport && c.swim_km
                ? `${km(c.swim_km)} · ${km(c.bike_km)} · ${km(c.run_km)}`
                : c.distance_km
                  ? km(c.distance_km)
                  : "-"}
            </span>
          ) : null}
          <span role="cell" className="num">
            {c.start_time || "-"}
          </span>
          {!court ? (
            <span role="cell" className="num">
              {c.cutoff_minutes ? minutesLabel(c.cutoff_minutes) : "-"}
            </span>
          ) : null}
          <span role="cell">
            <span className={`lvl lvl-${c.level}`}>{LEVEL_LABEL[c.level] || c.level}</span>
          </span>
          <span role="cell" className="num ct-fee">
            {c.fee_inr ? inr(c.fee_inr) : "-"}
          </span>
        </button>
      ))}
    </div>
  );
}

function MatchPanel({ event, athlete }) {
  if (!athlete) {
    return (
      <div className="panel panel-pad side-card">
        <p className="eyebrow">Is this event for you?</p>
        <p className="small" style={{ margin: "8px 0 14px" }}>
          Build a profile to see how well this event fits your level, with the reasons behind it.
        </p>
        <Link to="/start" className="btn btn-sm btn-ink">
          Build your profile
        </Link>
      </div>
    );
  }
  const inProfile = athlete.sports.some((s) => s.sport.slug === event.sport.slug);
  if (!athlete.recommendations_enabled) {
    return (
      <div className="panel panel-pad side-card">
        <p className="eyebrow">Your match</p>
        <p className="small muted" style={{ marginTop: 8 }}>
          Recommendations are off. Switch them on from Discover to see your fit.
        </p>
      </div>
    );
  }
  if (!inProfile || !event.match) {
    return (
      <div className="panel panel-pad side-card">
        <p className="eyebrow">Your match</p>
        <p className="small" style={{ margin: "8px 0 14px" }}>
          {event.sport.name} is not in your profile yet. Add it to get a match score for this event.
        </p>
        <Link to="/profile" className="btn btn-sm">
          Add {event.sport.name}
        </Link>
      </div>
    );
  }
  const m = event.match;
  return (
    <div className="panel panel-pad side-card match-card">
      <div className="panel-head">
        <p className="eyebrow">Your match</p>
        <MatchPill match={m} />
      </div>
      <p className="small muted">
        Best category for you: <b className="ink">{m.category_name}</b>
      </p>
      <ul className="reason-list">
        {m.reasons.map((r) => (
          <li key={r}>
            <Check size={14} weight="bold" /> {r}
          </li>
        ))}
        {m.cautions.map((r) => (
          <li key={r} className="caution">
            <Warning size={14} weight="bold" /> {r}
          </li>
        ))}
      </ul>
      <Link to={`/events/${event.slug}/readiness?cat=${m.category_id}`} className="btn btn-sm btn-ink">
        Check your readiness <ArrowRight size={14} />
      </Link>
    </div>
  );
}

function Countdown({ event }) {
  const d = event.days_until;
  const weeks = Math.floor(d / 7);
  return (
    <div className="panel panel-pad side-card countdown">
      <p className="eyebrow">Race clock</p>
      <div className="cd-digits">
        <span className="num">D-{Math.max(d, 0)}</span>
      </div>
      <p className="small muted">
        {weeks >= 1 ? `${weeksLabel(weeks)} to train` : "Race week"}
        {event.date_status === "expected" ? " · date expected" : ""}
      </p>
      <div className="cd-bar" aria-hidden="true">
        {Array.from({ length: 20 }).map((_, i) => (
          <span key={i} className={i < Math.max(0, 20 - Math.min(20, weeks)) ? "on" : ""} />
        ))}
      </div>
      <p className="cd-scale small muted">
        <span>20 wks out</span>
        <span>Race day</span>
      </p>
    </div>
  );
}

export default function Overview({ event, categoryId, setCategory, athlete }) {
  const course = event.course || {};
  const reg = event.registration;
  return (
    <div className="ev-grid">
      <div className="ev-main">
        <section className="ev-section">
          <p className="lede">{event.summary}</p>
          {event.highlights.length ? (
            <ul className="highlights">
              {event.highlights.map((h) => (
                <li key={h}>{h}</li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="ev-section">
          <div className="panel-head">
            <h2 className="section-title">Categories</h2>
            <span className="small muted">Pick one to use for readiness and registration</span>
          </div>
          <CategoryTable
            event={event}
            categoryId={categoryId}
            setCategory={setCategory}
            matchId={event.match?.category_id}
          />
        </section>

        <section className="ev-section">
          <h2 className="section-title">{event.sport.family === "court" || event.sport.family === "team" ? "Venue & format" : "Course"}</h2>
          <div className="course-grid">
            <div className="course-facts">
              {course.terrain ? (
                <div>
                  <span className="eyebrow">Terrain</span>
                  <b>{TERRAIN_LABEL[course.terrain] || course.terrain}</b>
                </div>
              ) : null}
              {course.surface ? (
                <div>
                  <span className="eyebrow">Surface</span>
                  <b>{sentenceCase(course.surface)}</b>
                </div>
              ) : null}
              {course.profile ? (
                <div>
                  <span className="eyebrow">Profile</span>
                  <b className="profile-word">
                    <ProfileGlyph profile={course.profile} /> {sentenceCase(course.profile)}
                  </b>
                </div>
              ) : null}
              {course.elevation_gain_m ? (
                <div>
                  <span className="eyebrow">Elevation gain</span>
                  <b className="num">
                    <Mountains size={15} /> {course.elevation_gain_m.toLocaleString("en-IN")} m
                  </b>
                </div>
              ) : null}
            </div>
            {course.description ? <p className="course-desc">{course.description}</p> : null}
            {event.format ? (
              <div className="callout callout-info" style={{ color: "var(--ink-2)" }}>
                <div>
                  <strong>Format</strong>
                  <div className="callout-body">{event.format}</div>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        {event.amenities.length ? (
          <section className="ev-section">
            <h2 className="section-title">What's included</h2>
            <ul className="amenities">
              {event.amenities.map((a) => (
                <li key={a}>
                  <Check size={14} weight="bold" /> {a}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {event.related.length ? (
          <section className="ev-section">
            <h2 className="section-title">More {event.sport.name.toLowerCase()} nearby</h2>
            <div className="related">
              {event.related.map((r) => (
                <Link key={r.slug} to={`/events/${r.slug}`} className="related-item">
                  <span className="eyebrow">{formatDate(r.start_date)}</span>
                  <b>{r.name}</b>
                  <span className="small muted">{r.city.name}</span>
                </Link>
              ))}
            </div>
          </section>
        ) : null}

        {event.sources.length ? (
          <section className="ev-section sources">
            <p className="eyebrow">Sources</p>
            <ul>
              {event.sources.map((s) => (
                <li key={s}>
                  <a href={s} target="_blank" rel="noreferrer">
                    {s.replace(/^https?:\/\/(www\.)?/, "").slice(0, 80)}
                  </a>
                </li>
              ))}
            </ul>
            {event.date_status === "expected" && event.last_edition_date ? (
              <p className="small muted">
                Last edition: {formatDate(event.last_edition_date)}. The date above follows that pattern and is not yet
                confirmed by the organiser.
              </p>
            ) : null}
          </section>
        ) : null}
      </div>

      <aside className="ev-aside">
        <MatchPanel event={event} athlete={athlete} />
        <Countdown event={event} />
        {event.weather ? (
          <div className="panel panel-pad side-card">
            <div className="panel-head">
              <p className="eyebrow">
                <Thermometer size={13} weight="bold" style={{ display: "inline", verticalAlign: "-2px" }} />{" "}
                {event.weather.month} in {event.city.name}
              </p>
            </div>
            <WeatherBand weather={event.weather} compact />
            <Link to={`/events/${event.slug}/guide`} className="side-link">
              Full event guide <ArrowRight size={14} />
            </Link>
          </div>
        ) : null}
        <div className="panel panel-pad side-card">
          <p className="eyebrow">Registration</p>
          <p style={{ margin: "8px 0 4px" }}>
            <span className={`reg-dot reg-${reg.status}`}>
              {{ open: "Open now", upcoming: "Opening soon", closed: "Closed", unknown: "Check with organiser" }[
                reg.status
              ]}
            </span>
          </p>
          {reg.opens ? <p className="small muted">Opens {formatDate(reg.opens)}</p> : null}
          {reg.closes ? <p className="small muted">Closes {formatDate(reg.closes)}</p> : null}
          {reg.notes ? <p className="small" style={{ marginTop: 8 }}>{reg.notes}</p> : null}
          {event.registrations_count ? (
            <p className="small muted" style={{ marginTop: 8 }}>
              {event.registrations_count} registered on StartLine
            </p>
          ) : null}
        </div>
      </aside>
    </div>
  );
}

export function ProfileGlyph({ profile }) {
  const d = {
    flat: "M1 9h22",
    rolling: "M1 10c4-4 6-4 9 0s6 4 9-1 4-3 4-3",
    hilly: "M1 12l5-7 4 5 4-7 5 9 4-4",
    mountain: "M1 13l7-11 5 7 3-3 7 7",
  }[profile];
  if (!d) return null;
  return (
    <svg width="26" height="14" viewBox="0 0 24 14" aria-hidden="true" style={{ display: "inline", verticalAlign: "-2px" }}>
      <path d={d} fill="none" stroke="var(--c)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
