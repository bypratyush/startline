import { ArrowRight, BookmarkSimple, Gauge, Ticket, Warning } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router";
import Bib from "../components/Bib.jsx";
import { Badge, DateBlock, EmptyState, ErrorState, Skeleton, SportTag, Toggle } from "../components/ui.jsx";
import SportIcon from "../icons/SportIcon.jsx";
import { api } from "../lib/api.js";
import { useAthlete } from "../lib/athlete.jsx";
import { daysUntilLabel, monthLabel, sportVar } from "../lib/format.js";

const VERDICT_TONE = { ready: "good", nearly: "info", build: "warn", "not-this-one": "bad" };

export default function Season() {
  const { athlete, loading, patch, toggleSaved } = useAthlete();
  const [season, setSeason] = useState(null);
  const [regs, setRegs] = useState([]);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    if (!athlete) return;
    setError(null);
    Promise.all([api.get(`/api/athletes/${athlete.id}/season`), api.get(`/api/athletes/${athlete.id}/registrations`)])
      .then(([s, r]) => {
        setSeason(s);
        setRegs(r);
      })
      .catch(setError);
  }, [athlete]);

  useEffect(load, [load]);

  if (loading) {
    return (
      <div className="container page">
        <Skeleton h={40} w="40%" />
        <Skeleton h={240} style={{ marginTop: 24 }} r={14} />
      </div>
    );
  }

  if (!athlete) {
    return (
      <div className="container page">
        <EmptyState
          title="Your season starts with a profile"
          action={
            <Link to="/start" className="btn btn-primary">
              Build your profile
            </Link>
          }
        >
          Save events, register, and StartLine lays them out as a season with recovery warnings between races.
        </EmptyState>
      </div>
    );
  }

  async function cancel(code) {
    await api.del(`/api/registrations/${code}?athlete_id=${athlete.id}`);
    load();
  }

  async function unsave(slug) {
    await toggleSaved(slug);
    load();
  }

  const timeline = season?.timeline || [];
  const next = timeline[0];
  const confirmed = regs.filter((r) => r.status === "confirmed");
  const groups = [];
  for (const t of timeline) {
    const key = t.event.start_date.slice(0, 7);
    if (!groups.length || groups[groups.length - 1].key !== key) groups.push({ key, items: [] });
    groups[groups.length - 1].items.push(t);
  }
  const warnFor = (slug) => (season?.warnings || []).filter((w) => w.events[1] === slug);

  return (
    <div className="container page season">
      <header className="season-head">
        <div>
          <p className="eyebrow">My season · 2026-27</p>
          <h1 className="page-title">{athlete.name}</h1>
          <div className="season-sports">
            {athlete.sports.map((s) => (
              <span key={s.sport.slug} className="season-sport" style={{ "--c": sportVar(s.sport.slug) }}>
                <SportIcon sport={s.sport.slug} size={15} strokeWidth={1.8} />
                {s.sport.name}
                <span className={`lvl lvl-${s.level}`}>{s.level}</span>
              </span>
            ))}
            <Link to="/profile" className="btn btn-sm btn-ghost">
              Edit profile
            </Link>
          </div>
        </div>
        <div className="season-toggle panel panel-pad">
          <Toggle
            id="season-recs"
            checked={athlete.recommendations_enabled}
            onChange={(v) => patch({ recommendations_enabled: v })}
            label="Recommendations"
            hint={athlete.recommendations_enabled ? "On: best matches first in Discover" : "Off: plain date-sorted lists"}
          />
        </div>
      </header>

      {error ? <ErrorState error={error} retry={load} /> : null}

      <div className="kpis">
        <div className="kpi">
          <span className="eyebrow">Next start line</span>
          <span className="kpi-num num">{next ? `D-${next.event.days_until}` : "-"}</span>
          <span className="small muted">{next ? next.event.name : "Nothing planned yet"}</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">Registered</span>
          <span className="kpi-num num">{confirmed.length}</span>
          <span className="small muted">bibs in hand</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">Saved</span>
          <span className="kpi-num num">{timeline.filter((t) => t.kind === "saved").length}</span>
          <span className="small muted">events on the shortlist</span>
        </div>
        <div className="kpi">
          <span className="eyebrow">Recovery flags</span>
          <span className={`kpi-num num${season?.warnings?.length ? " warn-text" : ""}`}>{season?.warnings?.length ?? 0}</span>
          <span className="small muted">races too close together</span>
        </div>
      </div>

      <div className="season-grid">
        <section>
          <h2 className="section-title">Season plan</h2>
          {!season ? (
            <Skeleton h={200} r={14} />
          ) : timeline.length === 0 ? (
            <EmptyState
              title="No events yet"
              action={
                <Link to="/" className="btn btn-ink btn-sm">
                  Find events <ArrowRight size={14} />
                </Link>
              }
            >
              Save events with the bookmark, or register, and they will line up here by month.
            </EmptyState>
          ) : (
            <div className="season-timeline">
              {groups.map((g) => {
                const l = monthLabel(g.key);
                return (
                  <div key={g.key} className="st-month">
                    <h3 className="st-month-head">
                      {l.short} <span className="num">{l.year}</span>
                    </h3>
                    <div className="st-items">
                      {g.items.map((t) => (
                        <div key={t.event.slug}>
                          {warnFor(t.event.slug).map((w) => (
                            <div key={w.message} className={`st-warn ${w.level}`}>
                              <Warning size={15} weight="bold" /> {w.message}
                            </div>
                          ))}
                          <article className={`st-item ${t.kind}`} style={{ "--c": sportVar(t.event.sport.slug) }}>
                            <DateBlock iso={t.event.start_date} status={t.event.date_status} compact />
                            <div className="st-body">
                              <div className="st-top">
                                <SportTag sport={t.event.sport} size="sm" />
                                {t.kind === "registered" ? (
                                  <Badge tone="ink">
                                    <Ticket size={11} weight="bold" /> Bib {t.registration.bib_number}
                                  </Badge>
                                ) : (
                                  <Badge>
                                    <BookmarkSimple size={11} weight="fill" /> Saved
                                  </Badge>
                                )}
                                {t.readiness ? (
                                  <Badge tone={VERDICT_TONE[t.readiness.verdict]} title={`Last check: ${t.readiness.category}`}>
                                    <Gauge size={11} weight="bold" /> {t.readiness.score} ready
                                  </Badge>
                                ) : null}
                              </div>
                              <Link to={`/events/${t.event.slug}`} className="si-name">
                                {t.event.name}
                              </Link>
                              <p className="small muted">
                                {t.category ? `${t.category.name} · ` : ""}
                                {t.event.city.name} · {daysUntilLabel(t.event.days_until)}
                              </p>
                              <div className="st-actions">
                                <Link className="btn btn-sm" to={`/events/${t.event.slug}/readiness${t.category ? `?cat=${t.category.id}` : ""}`}>
                                  Readiness
                                </Link>
                                <Link className="btn btn-sm" to={`/events/${t.event.slug}/guide`}>
                                  Guide
                                </Link>
                                {t.kind === "saved" ? (
                                  <>
                                    <Link className="btn btn-sm btn-ink" to={`/events/${t.event.slug}/register`}>
                                      Register
                                    </Link>
                                    <button className="btn btn-sm btn-ghost" onClick={() => unsave(t.event.slug)}>
                                      Remove
                                    </button>
                                  </>
                                ) : null}
                              </div>
                            </div>
                          </article>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <aside>
          <h2 className="section-title">Your bibs</h2>
          {regs.length === 0 ? (
            <p className="small muted">Registrations show up here as race bibs.</p>
          ) : (
            <div className="bib-stack">
              {regs.map((r) => (
                <div key={r.code} className="bib-wrap">
                  <Bib registration={r} compact />
                  <div className="bib-actions">
                    <Link className="small link" to={`/events/${r.event.slug}/guide?cat=${r.category.id}`}>
                      Event guide
                    </Link>
                    {r.status === "confirmed" ? (
                      <button className="small link-btn" onClick={() => cancel(r.code)}>
                        Cancel registration
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
