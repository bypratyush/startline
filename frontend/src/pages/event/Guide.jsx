import { ArrowSquareOut, Drop, MapTrifold, Wind } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { ErrorState, Skeleton } from "../../components/ui.jsx";
import { api, qs } from "../../lib/api.js";
import { usePersisted } from "../../lib/athlete.jsx";

const BAND_TONE = {
  comfortable: "good",
  caution: "warn",
  "extreme-caution": "warn",
  danger: "bad",
  "extreme-danger": "bad",
};

export function WeatherBand({ weather, compact }) {
  const tone = BAND_TONE[weather.band];
  // where "feels like" sits on a 20-45 C scale
  const pos = Math.max(0, Math.min(100, ((weather.feels_like_c - 20) / 25) * 100));
  return (
    <div className={`weather${compact ? " compact" : ""}`}>
      <div className="wx-top">
        <div>
          <span className="eyebrow">Feels like {weather.when}</span>
          <div className="wx-temp num">{Math.round(weather.feels_like_c)}°</div>
        </div>
        <div className="wx-stats">
          <span>
            <b className="num">{Math.round(weather.start_temp_c)}°</b> air
          </span>
          <span>
            <b className="num">
              {Math.round(weather.min_c)}° / {Math.round(weather.max_c)}°
            </b>{" "}
            low / high
          </span>
          {weather.humidity_pct !== null ? (
            <span>
              <Drop size={12} weight="bold" /> <b className="num">{Math.round(weather.humidity_pct)}%</b> humidity
            </span>
          ) : null}
          {weather.rain_mm !== null && !compact ? (
            <span>
              <b className="num">{Math.round(weather.rain_mm)} mm</b> rain in the month
            </span>
          ) : null}
        </div>
      </div>
      <div className="wx-scale" aria-hidden="true">
        <span className="wx-marker" style={{ left: `${pos}%` }} />
      </div>
      <div className="wx-scale-labels small muted" aria-hidden="true">
        <span>20°</span>
        <span>27° caution</span>
        <span>32° extreme</span>
        <span>39° danger</span>
      </div>
      <div className={`wx-advice tone-${tone}`}>
        <b>{weather.band_label}.</b> {weather.advice}
      </div>
      {weather.air_quality ? (
        <p className="wx-aq small">
          <Wind size={14} weight="bold" /> {weather.air_quality}
        </p>
      ) : null}
      {!compact ? <p className="small muted wx-src">{weather.source}. Long-term monthly averages, not a forecast.</p> : null}
    </div>
  );
}

function KitChecklist({ items, eventSlug }) {
  const [ticked, setTicked] = usePersisted(`startline.kit.${eventSlug}`, []);
  const set = new Set(ticked);
  const done = items.filter((k) => set.has(k.item)).length;
  return (
    <div className="panel panel-pad kit">
      <div className="panel-head">
        <h3 className="panel-title">Kit checklist</h3>
        <span className="num kit-count">
          {done}/{items.length}
        </span>
      </div>
      <div className="kit-bar" aria-hidden="true">
        <span style={{ width: `${items.length ? (done / items.length) * 100 : 0}%` }} />
      </div>
      <ul className="kit-list">
        {items.map((k) => (
          <li key={k.item}>
            <label className={`kit-item${set.has(k.item) ? " on" : ""}`}>
              <input
                type="checkbox"
                checked={set.has(k.item)}
                onChange={() =>
                  setTicked((prev) => (prev.includes(k.item) ? prev.filter((x) => x !== k.item) : [...prev, k.item]))
                }
              />
              <span className="kit-box" aria-hidden="true" />
              <span>
                <b>{k.item}</b>
                {k.why ? <span className="small muted"> {k.why}</span> : null}
              </span>
            </label>
          </li>
        ))}
      </ul>
      <p className="small muted">Ticks are saved in this browser.</p>
    </div>
  );
}

function Bullets({ title, items, tone }) {
  if (!items?.length) return null;
  return (
    <section className="guide-block">
      <h3 className="guide-title">{title}</h3>
      <ul className={`bullets${tone ? ` bullets-${tone}` : ""}`}>
        {items.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ul>
    </section>
  );
}

export default function Guide({ event, categoryId }) {
  const [guide, setGuide] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    setGuide(null);
    api
      .get(`/api/events/${event.slug}/guide` + qs({ category_id: categoryId }))
      .then(setGuide)
      .catch(setError);
  }, [event.slug, categoryId]);

  if (error) return <ErrorState error={error} />;
  if (!guide)
    return (
      <div className="guide-grid">
        <Skeleton h={300} r={14} />
        <Skeleton h={300} r={14} />
      </div>
    );

  return (
    <div className="guide">
      <div className="guide-intro">
        <p className="eyebrow">Event guide{guide.category ? ` · ${guide.category.name}` : ""}</p>
        <h2 className="section-title">Everything for race day</h2>
        <p className="small muted">
          Built from the organiser's published information, {event.sport.name.toLowerCase()} best practice and{" "}
          {event.city.name}'s climate for {guide.weather?.month || "that month"}. Switch category on the Overview tab.
        </p>
      </div>

      <div className="guide-grid">
        <div className="guide-main">
          {guide.weather ? (
            <section className="panel panel-pad">
              <h3 className="panel-title" style={{ marginBottom: 14 }}>
                Conditions to expect
              </h3>
              <WeatherBand weather={guide.weather} />
            </section>
          ) : null}

          {guide.timeline.length ? (
            <section className="panel panel-pad">
              <h3 className="panel-title" style={{ marginBottom: 6 }}>
                Race-day timeline
              </h3>
              {guide.category?.start_time ? (
                <p className="small muted" style={{ marginBottom: 14 }}>
                  Clock times assume the {guide.category.name} start at{" "}
                  <b className="num ink">{guide.category.start_time}</b>.
                </p>
              ) : (
                <p className="small muted" style={{ marginBottom: 14 }}>
                  Start time not published yet: times are shown relative to the start.
                </p>
              )}
              <ol className="timeline">
                {guide.timeline.map((t, i) => (
                  <li key={i} className={t.offset === "Start" ? "is-start" : ""}>
                    <span className="tl-when">
                      {t.clock ? <b className="num">{t.clock}</b> : null}
                      <span>{t.offset}</span>
                    </span>
                    <span className="tl-dot" aria-hidden="true" />
                    <span className="tl-what">{t.what}</span>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {guide.event_tips.length ? (
            <section className="panel panel-pad event-tips">
              <h3 className="panel-title">From this event</h3>
              <ul className="bullets bullets-accent">
                {guide.event_tips.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </section>
          ) : null}

          <div className="panel panel-pad guide-columns">
            <Bullets title="Fuel and hydration" items={guide.nutrition} />
            <Bullets title="Safety" items={guide.safety} tone="warn" />
            <Bullets title="First-timer tips" items={guide.beginner_tips} />
            <Bullets title="How to train for it" items={guide.training} />
          </div>

          {guide.glossary.length ? (
            <section className="panel panel-pad">
              <h3 className="panel-title" style={{ marginBottom: 12 }}>
                Glossary
              </h3>
              <dl className="glossary">
                {guide.glossary.map((g) => (
                  <div key={g.term}>
                    <dt>{g.term}</dt>
                    <dd>{g.meaning}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}
        </div>

        <aside className="guide-aside">
          {guide.kit.length ? <KitChecklist items={guide.kit} eventSlug={event.slug} /> : null}
          <div className="panel panel-pad">
            <h3 className="panel-title">Getting there</h3>
            <p className="small" style={{ margin: "8px 0 12px" }}>
              {guide.venue.name ? `${guide.venue.name}, ` : ""}
              {guide.venue.city}
            </p>
            {guide.venue.city_note ? <p className="small muted" style={{ marginBottom: 12 }}>{guide.venue.city_note}</p> : null}
            <div className="row" style={{ "--gap": "8px", flexWrap: "wrap" }}>
              <a className="btn btn-sm" href={guide.venue.maps_url} target="_blank" rel="noreferrer">
                <MapTrifold size={15} /> Open in Maps
              </a>
              {guide.official_url ? (
                <a className="btn btn-sm" href={guide.official_url} target="_blank" rel="noreferrer">
                  Organiser <ArrowSquareOut size={14} />
                </a>
              ) : null}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
