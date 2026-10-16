import { CaretRight, Check, X } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import EventCard from "../components/EventCard.jsx";
import { ErrorState, Skeleton, SportPattern } from "../components/ui.jsx";
import SportIcon from "../icons/SportIcon.jsx";
import { api } from "../lib/api.js";
import { sportVar } from "../lib/format.js";

export default function SportPage() {
  const { slug } = useParams();
  const [sport, setSport] = useState(null);
  const [error, setError] = useState(null);
  const [level, setLevel] = useState("beginner");

  useEffect(() => {
    setSport(null);
    api.get(`/api/sports/${slug}`).then(setSport).catch(setError);
  }, [slug]);

  if (error) return <div className="container page"><ErrorState error={error} /></div>;
  if (!sport)
    return (
      <div className="container page">
        <Skeleton h={48} w="40%" />
        <Skeleton h={300} style={{ marginTop: 24 }} r={14} />
      </div>
    );

  const rules = sport.recommendation_rules.find((r) => r.level === level);
  const g = sport.guide || {};
  return (
    <div className="sport-page" style={{ "--c": sportVar(sport.slug) }}>
      <section className="ev-hero sp-hero">
        <SportPattern family={sport.family} slug={sport.slug} />
        <div className="container ev-hero-inner">
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link to="/sports">Sports</Link>
            <CaretRight size={11} weight="bold" />
            <span>{sport.name}</span>
          </nav>
          <div className="sp-title-row">
            <span className="sp-icon">
              <SportIcon sport={sport.slug} size={34} strokeWidth={1.5} />
            </span>
            <div>
              <h1 className="ev-title">{sport.name}</h1>
              <p className="ev-sub">{sport.tagline}</p>
            </div>
          </div>
          <p className="lede" style={{ marginTop: 14 }}>
            {sport.description}
          </p>
          <div className="row" style={{ "--gap": "10px", marginTop: 18, flexWrap: "wrap" }}>
            <Link className="btn btn-primary" to={`/?sports=${sport.slug}`}>
              {sport.events.length} upcoming events
            </Link>
          </div>
        </div>
      </section>

      <div className="container sp-body">
        <div className="sp-grid">
          <section className="panel panel-pad">
            <h2 className="panel-title">Formats</h2>
            <dl className="disciplines">
              {sport.disciplines.map((d) => (
                <div key={d.slug || d.name}>
                  <dt>{d.name}</dt>
                  <dd className="small muted">{d.description}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="panel panel-pad">
            <div className="panel-head">
              <h2 className="panel-title">What suits your level</h2>
              <div className="segmented segmented-sm" role="radiogroup" aria-label="Level">
                {["beginner", "intermediate", "advanced"].map((l) => (
                  <button key={l} type="button" role="radio" aria-checked={level === l} className={level === l ? "on" : ""} onClick={() => setLevel(l)}>
                    {l[0].toUpperCase() + l.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <p className="small" style={{ marginBottom: 14 }}>
              {sport.level_definitions?.[level]}
            </p>
            {rules ? (
              <div className="suits">
                <ul className="suit-list good">
                  {rules.suits.map((s) => (
                    <li key={s.format}>
                      <Check size={14} weight="bold" />
                      <div>
                        <b>{s.format}</b>
                        {s.reason ? <span className="small muted"> {s.reason}</span> : null}
                      </div>
                    </li>
                  ))}
                </ul>
                <ul className="suit-list avoid">
                  {rules.avoid.map((s) => (
                    <li key={s.format}>
                      <X size={14} weight="bold" />
                      <div>
                        <b>{s.format}</b>
                        {s.reason ? <span className="small muted"> {s.reason}</span> : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="panel panel-pad">
            <h2 className="panel-title">The questions we ask</h2>
            <p className="small muted" style={{ margin: "6px 0 12px" }}>
              Your answers set your level and what you can comfortably handle.
            </p>
            <ol className="q-list">
              {sport.questions.map((q) => (
                <li key={q.id}>
                  <b>{q.prompt}</b>
                  <span className="small muted">{q.options.map((o) => o.label).join(" · ")}</span>
                </li>
              ))}
            </ol>
          </section>

          <section className="panel panel-pad">
            <h2 className="panel-title">How to train</h2>
            <ul className="bullets" style={{ marginTop: 10 }}>
              {(g.training || []).map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </section>
        </div>

        {g.glossary?.length ? (
          <section className="panel panel-pad" style={{ marginTop: 20 }}>
            <h2 className="panel-title" style={{ marginBottom: 12 }}>
              Glossary
            </h2>
            <dl className="glossary">
              {g.glossary.map((x) => (
                <div key={x.term}>
                  <dt>{x.term}</dt>
                  <dd>{x.meaning}</dd>
                </div>
              ))}
            </dl>
          </section>
        ) : null}

        <section style={{ marginTop: 36 }}>
          <h2 className="section-title">
            Upcoming {sport.name.toLowerCase()} <span className="count">{sport.events.length}</span>
          </h2>
          <div className="card-list" style={{ marginTop: 14 }}>
            {sport.events.map((e) => (
              <EventCard key={e.slug} event={e} showMatch={false} />
            ))}
          </div>
        </section>

        {sport.sources?.length ? (
          <section className="sources" style={{ marginTop: 28 }}>
            <p className="eyebrow">Sources</p>
            <ul>
              {sport.sources.slice(0, 12).map((s) => {
                const url = typeof s === "string" ? s : s.url;
                return url ? (
                  <li key={url}>
                    <a href={url} target="_blank" rel="noreferrer">
                      {(typeof s === "string" ? url : s.title || url).replace(/^https?:\/\/(www\.)?/, "").slice(0, 90)}
                    </a>
                  </li>
                ) : null;
              })}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}
