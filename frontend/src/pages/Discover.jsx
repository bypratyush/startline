import { Crosshair, MagnifyingGlass, MapPin, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import EventCard from "../components/EventCard.jsx";
import { EmptyState, ErrorState, Segmented, Select, Skeleton, Toggle } from "../components/ui.jsx";
import SportIcon from "../icons/SportIcon.jsx";
import { api, qs } from "../lib/api.js";
import { useAthlete, usePersisted } from "../lib/athlete.jsx";
import { monthLabel, plural, sportVar } from "../lib/format.js";

const RADII = [
  { value: "", label: "Any" },
  { value: "50", label: "50" },
  { value: "150", label: "150" },
  { value: "400", label: "400 km" },
];

// A start line under the words "start line": a short tick, then the line painted out from it.
function ChalkStroke() {
  return (
    <svg className="chalk-stroke" viewBox="0 0 300 16" preserveAspectRatio="none" aria-hidden="true">
      <path d="M1.5 2v12" />
      <path className="rule" d="M1.5 8H300" />
    </svg>
  );
}

function nearestCity(cities, lat, lon) {
  const rad = (d) => (d * Math.PI) / 180;
  let best = null;
  let bestD = Infinity;
  for (const c of cities) {
    const dLat = rad(c.lat - lat);
    const dLon = rad(c.lon - lon);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(rad(lat)) * Math.cos(rad(c.lat)) * Math.sin(dLon / 2) ** 2;
    const d = 12742 * Math.asin(Math.sqrt(a));
    if (d < bestD) {
      bestD = d;
      best = c;
    }
  }
  return best;
}

function SportRail({ sports, selected, onToggle, onAll, facet }) {
  return (
    <div className="sport-rail" role="group" aria-label="Sports">
      <button type="button" className={`sport-chip all${selected.length === 0 ? " on" : ""}`} onClick={onAll}>
        <span>All sports</span>
      </button>
      {sports.map((s) => {
        const on = selected.includes(s.slug);
        const n = facet ? facet[s.slug] || 0 : s.events;
        return (
          <button
            key={s.slug}
            type="button"
            className={`sport-chip${on ? " on" : ""}${n === 0 ? " empty" : ""}`}
            style={{ "--c": sportVar(s.slug) }}
            aria-pressed={on}
            onClick={() => onToggle(s.slug)}
          >
            <SportIcon sport={s.slug} size={16} strokeWidth={1.8} />
            <span>{s.name}</span>
            <span className="chip-count">{n}</span>
          </button>
        );
      })}
    </div>
  );
}

function ProfileCard({ athlete, recsOn, setRecs, sportBySlug }) {
  if (!athlete) {
    return (
      <div className="profile-card cta">
        <p className="eyebrow">For you</p>
        <h3>See the events that fit you first</h3>
        <ol className="cta-steps">
          <li>Your home city</li>
          <li>Your sports</li>
          <li>Two or three quick questions for each</li>
        </ol>
        <Link to="/start" className="btn btn-primary">
          Build your profile
        </Link>
        <span className="small muted">Under a minute. No password.</span>
      </div>
    );
  }
  return (
    <div className="profile-card">
      <div className="pc-head">
        <div>
          <p className="eyebrow">Your profile</p>
          <h3>{athlete.name.split(" ")[0]}</h3>
          <p className="small muted">{athlete.city?.name}</p>
        </div>
        <Link to="/profile" className="btn btn-sm">
          Edit
        </Link>
      </div>
      <ul className="pc-sports">
        {athlete.sports.map((s) => (
          <li key={s.sport.slug} style={{ "--c": sportVar(s.sport.slug) }}>
            <SportIcon sport={s.sport.slug} size={15} strokeWidth={1.8} />
            <span>{sportBySlug[s.sport.slug]?.name || s.sport.name}</span>
            <span className="pc-level">{s.level}</span>
          </li>
        ))}
      </ul>
      <div className="pc-toggle">
        <Toggle
          id="recs"
          checked={recsOn}
          onChange={setRecs}
          label="Recommendations"
          hint={recsOn ? "Best matches first, with the reasons" : "Off: a plain list by date"}
        />
      </div>
    </div>
  );
}

function groupByMonth(items) {
  const groups = [];
  for (const e of items) {
    const key = e.start_date.slice(0, 7);
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) {
      g = { key, items: [] };
      groups.push(g);
    }
    g.items.push(e);
  }
  return groups;
}

export default function Discover() {
  const { athlete, loading: athleteLoading, sports, cities, patch, catalogLoaded } = useAthlete();
  const [params, setParams] = useSearchParams();
  const [guestCity, setGuestCity] = usePersisted("startline.city", "");
  const [stats, setStats] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(params.get("q") || "");
  const [reload, setReload] = useState(0);
  const [showAllPicks, setShowAllPicks] = useState(false);
  const searchTimer = useRef(null);

  const profileSports = useMemo(() => (athlete ? athlete.sports.map((s) => s.sport.slug) : []), [athlete]);
  const sportsParam = params.get("sports");
  const selected = sportsParam === "all" ? [] : sportsParam ? sportsParam.split(",") : profileSports;
  const cityParam = params.get("city");
  const city = cityParam === "any" ? "" : (cityParam ?? (athlete?.city?.slug || guestCity || ""));
  const radius = params.get("radius") || "";
  const month = params.get("month") || "";
  const level = params.get("level") || "";
  const openOnly = params.get("open") === "1";
  const beginner = params.get("beginner") === "1";
  const sort = params.get("sort") || "recommended";
  const recsOn = athlete ? athlete.recommendations_enabled : false;

  function update(next) {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v === "" || v === null || v === undefined || v === false) p.delete(k);
      else p.set(k, v);
    }
    setParams(p, { replace: true });
  }

  useEffect(() => {
    api.get("/api/stats").then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (athleteLoading) return;
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    api
      .get(
        "/api/events" +
          qs({
            sport: selected.length ? selected.join(",") : undefined,
            city: city || undefined,
            radius_km: city && radius ? radius : undefined,
            month: month || undefined,
            level: level || undefined,
            registration: openOnly ? "open" : undefined,
            beginner_friendly: beginner ? "true" : undefined,
            q: params.get("q") || undefined,
            sort,
            athlete_id: athlete?.id,
            recommend: recsOn ? "true" : "false",
          }),
        { signal: ctrl.signal },
      )
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        if (e.name === "AbortError") return;
        setError(e);
        setLoading(false);
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, athlete?.id, recsOn, athleteLoading, reload, guestCity]);

  function toggleSport(slug) {
    const next = selected.includes(slug) ? selected.filter((s) => s !== slug) : [...selected, slug];
    update({ sports: next.length ? next.join(",") : "all" });
  }

  function onSearch(v) {
    setQuery(v);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => update({ q: v.trim() }), 280);
  }

  function setCity(slug) {
    if (!athlete) setGuestCity(slug);
    update({ city: slug || "any", radius: slug ? radius : "" });
  }

  function locate() {
    if (!navigator.geolocation || !cities.length) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      const c = nearestCity(cities, pos.coords.latitude, pos.coords.longitude);
      if (c) setCity(c.slug);
    });
  }

  const items = data?.items || [];
  const picked = data?.recommendations === "on" && sort === "recommended" ? items.filter((e) => e.recommended) : [];
  const PICKS = 6;
  const shownPicks = showAllPicks ? picked : picked.slice(0, PICKS);
  const shownSlugs = new Set(shownPicks.map((e) => e.slug));
  // matches beyond the top six fall back into the month-by-month list, keeping their badges
  const rest = picked.length ? items.filter((e) => !shownSlugs.has(e.slug)).sort((a, b) => a.start_date.localeCompare(b.start_date)) : items;
  const sortedRest = sort === "distance" ? null : groupByMonth(rest);
  const monthOptions = data ? Object.keys(data.facets.months) : [];
  const activeFilters = [month, level, openOnly, beginner, params.get("q"), radius].filter(Boolean).length;
  const tier1 = cities.filter((c) => c.tier === 1);
  const tier2 = cities.filter((c) => c.tier === 2);

  return (
    <>
      <section className="discover-hero">
        <div className="container dh-grid">
          <div className="dh-copy">
            <p className="eyebrow">Season 2026-27 · India</p>
            <h1 className="dh-title">
              Find your next{" "}
              <span className="chalk">
                start line
                <ChalkStroke />
              </span>
            </h1>
            <p className="lede">
              Real marathons, brevets, sea swims, triathlons and tournaments across India's Tier 1 and Tier 2 cities.
              Pick your sports, check you are ready, then register.
            </p>
            <dl className="dh-stats">
              <div>
                <dt>Events</dt>
                <dd className="num">{stats ? stats.events_upcoming : "-"}</dd>
              </div>
              <div>
                <dt>Cities</dt>
                <dd className="num">{stats ? stats.cities_with_events : "-"}</dd>
              </div>
              <div>
                <dt>Sports</dt>
                <dd className="num">{stats ? stats.sports : "-"}</dd>
              </div>
            </dl>
          </div>
          <div className="dh-side">
            {athleteLoading ? (
              <div className="profile-card">
                <Skeleton h={18} w="40%" />
                <Skeleton h={30} w="70%" style={{ marginTop: 10 }} />
                <Skeleton h={60} style={{ marginTop: 16 }} />
              </div>
            ) : (
              <ProfileCard
                athlete={athlete}
                recsOn={recsOn}
                setRecs={(v) => patch({ recommendations_enabled: v })}
                sportBySlug={Object.fromEntries(sports.map((s) => [s.slug, s]))}
              />
            )}
          </div>
        </div>
      </section>

      <section className="filters" aria-label="Filters">
        <div className="container">
          {catalogLoaded ? (
            <SportRail
              sports={sports}
              selected={selected}
              onToggle={toggleSport}
              onAll={() => update({ sports: "all" })}
              facet={data?.facets.sports}
            />
          ) : (
            <div className="sport-rail">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} h={38} w={120} r={999} />
              ))}
            </div>
          )}
          <div className="filter-row">
            <Select label="City" value={city} onChange={setCity} icon={<MapPin size={14} weight="bold" />} className="city-select">
              <option value="">All cities</option>
              <optgroup label="Tier 1">
                {tier1.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.name} ({c.events})
                  </option>
                ))}
              </optgroup>
              <optgroup label="Tier 2">
                {tier2.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.name} ({c.events})
                  </option>
                ))}
              </optgroup>
            </Select>
            <button type="button" className="icon-btn locate" onClick={locate} title="Use my location" aria-label="Use my location">
              <Crosshair size={16} />
            </button>
            {city ? (
              <Segmented label="Distance" options={RADII} value={radius} onChange={(v) => update({ radius: v })} size="sm" />
            ) : null}
            <Select label="Month" value={month} onChange={(v) => update({ month: v })}>
              <option value="">Any month</option>
              {(month && !monthOptions.includes(month) ? [month, ...monthOptions] : monthOptions).map((m) => {
                const l = monthLabel(m);
                return (
                  <option key={m} value={m}>
                    {l.month} {l.year}
                  </option>
                );
              })}
            </Select>
            <Select label="Level" value={level} onChange={(v) => update({ level: v })}>
              <option value="">Any level</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </Select>
            <button
              type="button"
              className={`filter-pill${openOnly ? " on" : ""}`}
              aria-pressed={openOnly}
              onClick={() => update({ open: openOnly ? "" : "1" })}
            >
              Entries open
            </button>
            <button
              type="button"
              className={`filter-pill${beginner ? " on" : ""}`}
              aria-pressed={beginner}
              onClick={() => update({ beginner: beginner ? "" : "1" })}
            >
              Beginner friendly
            </button>
            <div className="search">
              <MagnifyingGlass size={16} />
              <input
                type="search"
                placeholder="Search"
                value={query}
                onChange={(e) => onSearch(e.target.value)}
                aria-label="Search events"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="container results">
        <div className="results-bar">
          <p className="small muted">
            {loading ? (
              "Finding events…"
            ) : data ? (
              <>
                <b className="results-count">{plural(data.total, "event")}</b>
                {selected.length ? ` in ${selected.length === 1 ? "1 sport" : `${selected.length} sports`}` : ""}
                {data.origin ? ` · distances from ${data.origin.name}` : ""}
              </>
            ) : null}
            {activeFilters ? (
              <button
                type="button"
                className="clear-filters"
                onClick={() => {
                  setQuery("");
                  update({ month: "", level: "", open: "", beginner: "", q: "", radius: "" });
                }}
              >
                <X size={12} weight="bold" /> Clear filters
              </button>
            ) : null}
          </p>
          <Select label="Sort" value={sort} onChange={(v) => update({ sort: v === "recommended" ? "" : v })}>
            <option value="recommended">{recsOn ? "Best match first" : "Soonest first"}</option>
            <option value="date">Soonest first</option>
            {city ? <option value="distance">Nearest first</option> : null}
          </Select>
        </div>

        {error ? (
          <ErrorState error={error} retry={() => setReload((n) => n + 1)} />
        ) : loading && !data ? (
          <div className="card-list">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="ec" style={{ padding: 18 }}>
                <Skeleton h={72} />
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState
            title="No events on this start line"
            action={
              <button className="btn btn-sm" onClick={() => setParams({ sports: "all" })}>
                Show all events
              </button>
            }
          >
            Try another city, widen the distance, or pick more sports.
          </EmptyState>
        ) : (
          <div className={`results-body${loading ? " is-loading" : ""}`}>
            {picked.length ? (
              <div className="picked">
                <div className="picked-head">
                  <h2 className="section-title">
                    For you <span className="count">best {Math.min(PICKS, picked.length)} of {plural(picked.length, "match", "matches")}</span>
                  </h2>
                  <p className="small muted picked-note">
                    Ranked by your level, what you can comfortably handle, distance from home and weeks left to
                    prepare.
                  </p>
                </div>
                <div className="card-list">
                  {shownPicks.map((e) => (
                    <EventCard key={e.slug} event={e} />
                  ))}
                </div>
                {picked.length > PICKS ? (
                  <button type="button" className="btn btn-sm picked-more" onClick={() => setShowAllPicks((v) => !v)}>
                    {showAllPicks ? "Show top six only" : `Show all ${picked.length} matches, best first`}
                  </button>
                ) : null}
              </div>
            ) : null}
            {rest.length ? (
              <div className="all-events">
                {picked.length ? (
                  <h2 className="section-title">
                    More events <span className="count">{rest.length}</span>
                  </h2>
                ) : null}
                {sortedRest ? (
                  sortedRest.map((g) => {
                    const l = monthLabel(g.key);
                    return (
                      <div key={g.key} className="month-group">
                        <h3 className="month-head">
                          <span>{l.month}</span>
                          <span className="num">{l.year}</span>
                          <span className="month-count">{plural(g.items.length, "event")}</span>
                        </h3>
                        <div className="card-list">
                          {g.items.map((e) => (
                            <EventCard key={e.slug} event={e} />
                          ))}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="card-list">
                    {rest.map((e) => (
                      <EventCard key={e.slug} event={e} />
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
      </section>
    </>
  );
}
