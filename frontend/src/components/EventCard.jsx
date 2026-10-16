import { BookmarkSimple, Check } from "@phosphor-icons/react";
import { Link, useNavigate } from "react-router";
import SportIcon from "../icons/SportIcon.jsx";
import { useAthlete } from "../lib/athlete.jsx";
import { dateParts, daysUntilLabel, distanceTag, inr, sportVar } from "../lib/format.js";
import { MatchRing } from "./ui.jsx";

const FAMILY = { running: "run", "trail-running": "run", cycling: "ride", swimming: "swim", triathlon: "tri" };

const STATUS = { open: "Entries open", upcoming: "Opens soon", closed: "Entries closed", unknown: "" };

function catLabel(cat, family) {
  return distanceTag(cat, family) || (cat.name.length > 24 ? cat.name.slice(0, 23) + "…" : cat.name);
}

export function SaveButton({ slug, className = "" }) {
  const { athlete, saved, toggleSaved } = useAthlete();
  const navigate = useNavigate();
  const on = saved.has(slug);
  return (
    <button
      type="button"
      className={`save-btn${on ? " on" : ""} ${className}`}
      aria-pressed={on}
      title={athlete ? (on ? "Remove from your season" : "Save to your season") : "Build a profile to save events"}
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        if (!athlete) navigate("/start");
        else toggleSaved(slug);
      }}
    >
      <BookmarkSimple size={17} weight={on ? "fill" : "regular"} />
      <span className="visually-hidden">{on ? "Saved" : "Save"}</span>
    </button>
  );
}

export default function EventCard({ event, showMatch = true }) {
  const family = FAMILY[event.sport.slug] || event.sport.family;
  const d = dateParts(event.start_date);
  const cats = event.categories || [];
  const shown = cats.slice(0, 4);
  const match = showMatch ? event.match : null;
  const where = [event.city.name, event.distance_km != null ? (event.distance_km <= 15 ? "in your city" : `${event.distance_km} km away`) : null]
    .filter(Boolean)
    .join(" · ");
  return (
    <article className={`ec${match ? " is-match" : ""}`} style={{ "--c": sportVar(event.sport.slug) }}>
      <Link to={`/events/${event.slug}`} className="ec-link">
        <div className={`ec-date${event.date_status === "expected" ? " est" : ""}`}>
          <span className="ec-day num">{d.day}</span>
          <span className="ec-mon">{d.month}</span>
          <span className="ec-wd">{event.date_status === "expected" ? "expected" : d.weekday}</span>
        </div>
        <div className="ec-main">
          <p className="ec-kicker">
            <SportIcon sport={event.sport.slug} size={14} strokeWidth={1.9} />
            <span>{event.sport.name}</span>
            <span className="sep" />
            <span>{where}</span>
          </p>
          <h3 className="ec-title">{event.name}</h3>
          {shown.length ? (
            <p className="ec-cats">
              {shown.map((c, i) => (
                <span key={c.id} className={match && match.category_id === c.id ? "hit" : ""}>
                  {i ? <i aria-hidden="true">·</i> : null}
                  {catLabel(c, family)}
                </span>
              ))}
              {cats.length > shown.length ? <span className="more">+{cats.length - shown.length}</span> : null}
            </p>
          ) : null}
          {match && match.reasons.length ? (
            <p className="ec-why">
              <Check size={13} weight="bold" />
              <span>{match.reasons.slice(0, 2).join(" · ")}</span>
            </p>
          ) : null}
        </div>
        <div className="ec-side">
          {match ? <MatchRing match={match} /> : null}
          <span className="ec-fee num">{event.fee_min ? `from ${inr(event.fee_min)}` : ""}</span>
          <span className={`ec-status st-${event.registration_status}`}>
            {STATUS[event.registration_status] || daysUntilLabel(event.days_until)}
          </span>
          {STATUS[event.registration_status] ? <span className="ec-when">{daysUntilLabel(event.days_until)}</span> : null}
        </div>
      </Link>
      <SaveButton slug={event.slug} className="ec-save" />
    </article>
  );
}
