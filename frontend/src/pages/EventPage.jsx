import { ArrowSquareOut, CalendarPlus, CaretRight, MapPin } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link, NavLink, useParams, useSearchParams } from "react-router";
import { SaveButton } from "../components/EventCard.jsx";
import { Badge, ErrorState, Skeleton, SportPattern, SportTag } from "../components/ui.jsx";
import { api, qs } from "../lib/api.js";
import { useAthlete } from "../lib/athlete.jsx";
import { feeRange, formatRange, minutesLabel, REG_LABEL, sportVar } from "../lib/format.js";
import Guide from "./event/Guide.jsx";
import Overview from "./event/Overview.jsx";
import Readiness from "./event/Readiness.jsx";
import Register from "./event/Register.jsx";

const TABS = [
  { key: "", label: "Overview" },
  { key: "guide", label: "Event guide" },
  { key: "readiness", label: "Readiness" },
  { key: "register", label: "Register" },
];

function distancesSummary(e) {
  const fam = e.sport.family;
  const ds = e.categories.map((c) => c.distance_km).filter(Boolean);
  if (!ds.length || fam === "court" || fam === "team") return `${e.categories.length} categories`;
  const uniq = [...new Set(ds)].sort((a, b) => a - b);
  const fmt = (d) => (d < 1 ? `${Math.round(d * 1000)} m` : `${Number(d.toFixed(1))} km`);
  if (uniq.length <= 3) return uniq.map(fmt).join(" · ");
  return `${fmt(uniq[0])} to ${fmt(uniq[uniq.length - 1])}`;
}

export default function EventPage() {
  const { slug, tab = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const { athlete, loading: athleteLoading } = useAthlete();
  const [event, setEvent] = useState(null);
  const [error, setError] = useState(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    if (athleteLoading) return;
    setError(null);
    api
      .get(`/api/events/${slug}` + qs({ athlete_id: athlete?.id }))
      .then(setEvent)
      .catch(setError);
  }, [slug, athlete?.id, athlete?.recommendations_enabled, athleteLoading, reload]);

  const catParam = Number(params.get("cat")) || null;
  const categoryId =
    (event && event.categories.some((c) => c.id === catParam) && catParam) ||
    event?.match?.category_id ||
    event?.categories[0]?.id ||
    null;
  const setCategory = (id) => {
    const p = new URLSearchParams(params);
    p.set("cat", String(id));
    setParams(p, { replace: true });
  };

  if (error) {
    return (
      <div className="container" style={{ paddingTop: 48 }}>
        {error.status === 404 ? (
          <div className="empty">
            <h3>Event not found</h3>
            <Link to="/" className="btn btn-sm">
              Back to Discover
            </Link>
          </div>
        ) : (
          <ErrorState error={error} retry={() => setReload((n) => n + 1)} />
        )}
      </div>
    );
  }

  if (!event) {
    return (
      <div className="container" style={{ paddingTop: 40 }}>
        <Skeleton h={14} w={180} />
        <Skeleton h={54} w="60%" style={{ marginTop: 18 }} />
        <Skeleton h={18} w="40%" style={{ marginTop: 14 }} />
        <Skeleton h={84} style={{ marginTop: 28 }} r={14} />
        <Skeleton h={320} style={{ marginTop: 28 }} r={14} />
      </div>
    );
  }

  const cat = event.categories.find((c) => c.id === categoryId);
  const fee = feeRange(event.fee_min, event.fee_max);
  const firstStart = event.categories.find((c) => c.start_time)?.start_time;
  const cutoff = cat?.cutoff_minutes ? minutesLabel(cat.cutoff_minutes) : null;
  const tabProps = { event, cat, categoryId, setCategory, athlete };

  return (
    <div className="event-page" style={{ "--c": sportVar(event.sport.slug) }}>
      <section className="ev-hero">
        <SportPattern family={event.sport.family} slug={event.sport.slug} />
        <div className="container ev-hero-inner">
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link to="/">Discover</Link>
            <CaretRight size={11} weight="bold" />
            <Link to={`/sports/${event.sport.slug}`}>{event.sport.name}</Link>
            <CaretRight size={11} weight="bold" />
            <span>{event.city.name}</span>
          </nav>
          <div className="ev-hero-grid">
            <div className="ev-title-block">
              <div className="ev-tags">
                <SportTag sport={event.sport} />
                {event.discipline ? <span className="ev-disc">{event.discipline.replaceAll("-", " ")}</span> : null}
                {event.date_status === "expected" ? (
                  <Badge tone="warn" title="Based on the usual weekend of previous editions">
                    Date expected
                  </Badge>
                ) : null}
              </div>
              <h1 className="ev-title">{event.name}</h1>
              <p className="ev-sub">
                {[event.edition, event.organiser ? `by ${event.organiser}` : null].filter(Boolean).join(" · ")}
              </p>
              <p className="ev-where">
                <MapPin size={16} weight="bold" />
                <span>
                  {event.venue ? `${event.venue}, ` : ""}
                  {event.city.name}
                  {event.city.state !== event.city.name ? `, ${event.city.state}` : ""}
                </span>
              </p>
              {event.distance_km !== null && event.distance_km !== undefined && athlete ? (
                <p className="ev-away">
                  {event.distance_km <= 15 ? "In your city" : `${event.distance_km} km from ${athlete.city?.name}`}
                </p>
              ) : null}
            </div>
            <div className="ev-actions">
              <Link to={`/events/${event.slug}/register${categoryId ? `?cat=${categoryId}` : ""}`} className="btn btn-primary btn-lg">
                Register
              </Link>
              <div className="ev-actions-row">
                <SaveButton slug={event.slug} className="btn-icon" />
                <a
                  className="btn btn-sm"
                  href={`/api/events/${event.slug}/calendar.ics${categoryId ? `?category_id=${categoryId}` : ""}`}
                  title="Add to your calendar (.ics)"
                >
                  <CalendarPlus size={16} /> Calendar
                </a>
                {event.official_url ? (
                  <a className="btn btn-sm" href={event.official_url} target="_blank" rel="noreferrer">
                    Official site <ArrowSquareOut size={14} />
                  </a>
                ) : null}
              </div>
            </div>
          </div>

          <dl className="race-card">
            <div>
              <dt>Date</dt>
              <dd>{formatRange(event.start_date, event.end_date)}</dd>
            </div>
            <div>
              <dt>{event.sport.family === "court" || event.sport.family === "team" ? "Draws" : "Distances"}</dt>
              <dd>{distancesSummary(event)}</dd>
            </div>
            <div>
              <dt>First start</dt>
              <dd className="num">{firstStart || "TBA"}</dd>
            </div>
            <div>
              <dt>Cutoff{cat ? ` (${cat.name.length > 16 ? "selected" : cat.name})` : ""}</dt>
              <dd className="num">{cutoff || "Not published"}</dd>
            </div>
            <div>
              <dt>Entry</dt>
              <dd className="num">{fee || "See organiser"}</dd>
            </div>
            <div>
              <dt>Registration</dt>
              <dd>
                <span className={`reg-dot reg-${event.registration_status}`}>{REG_LABEL[event.registration_status]}</span>
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <div className="ev-tabs">
        <div className="container">
          <nav className="tabs" aria-label="Event sections">
            {TABS.map((t, i) => (
              <NavLink
                key={t.key}
                end
                to={`/events/${event.slug}${t.key ? `/${t.key}` : ""}${categoryId ? `?cat=${categoryId}` : ""}`}
                className={({ isActive }) => (isActive ? "active" : "")}
                replace
              >
                <span className="tab-num">{String(i + 1).padStart(2, "0")}</span>
                {t.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      <div className="container ev-body">
        {tab === "" ? <Overview {...tabProps} /> : null}
        {tab === "guide" ? <Guide {...tabProps} /> : null}
        {tab === "readiness" ? <Readiness {...tabProps} /> : null}
        {tab === "register" ? <Register {...tabProps} /> : null}
      </div>
    </div>
  );
}
