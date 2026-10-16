import { ArrowRight, Info, Timer } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import TrackGauge from "../../components/TrackGauge.jsx";
import { Callout, ErrorState, Skeleton } from "../../components/ui.jsx";
import { api, qs } from "../../lib/api.js";
import { formatDate, weeksLabel } from "../../lib/format.js";

function CategoryPills({ event, categoryId, setCategory }) {
  return (
    <div className="cat-pills" role="radiogroup" aria-label="Category">
      {event.categories.map((c) => (
        <button
          key={c.id}
          type="button"
          role="radio"
          aria-checked={c.id === categoryId}
          className={c.id === categoryId ? "on" : ""}
          onClick={() => setCategory(c.id)}
        >
          {c.name}
        </button>
      ))}
    </div>
  );
}

function Field({ f, value, onChange }) {
  if (f.type === "choice") {
    return (
      <label className="field">
        <span className="field-label">{f.label}</span>
        <select value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
          {f.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {f.help ? <span className="field-hint">{f.help}</span> : null}
      </label>
    );
  }
  if (f.type === "duration") {
    return (
      <label className="field">
        <span className="field-label">{f.label}</span>
        <div className="input-unit">
          <input
            className="input"
            inputMode="numeric"
            placeholder={f.format}
            value={value ?? ""}
            pattern="^\d{1,2}(:\d{2}){1,2}$"
            onChange={(e) => onChange(e.target.value)}
            required
          />
          <span className="unit">{f.format}</span>
        </div>
        {f.help ? <span className="field-hint">{f.help}</span> : null}
      </label>
    );
  }
  return (
    <label className="field">
      <span className="field-label">{f.label}</span>
      <div className="input-unit">
        <input
          className="input"
          type="number"
          inputMode="decimal"
          min={f.min}
          max={f.max}
          step={f.step}
          value={value ?? ""}
          onChange={(e) => onChange(e.target.value)}
          required
        />
        <span className="unit">{f.unit}</span>
      </div>
      {f.help ? <span className="field-hint">{f.help}</span> : null}
    </label>
  );
}

function Result({ result, event }) {
  const p = result.prediction;
  const verdictTone = { ready: "good", nearly: "info", build: "warn", "not-this-one": "bad" }[result.verdict];
  const totalSplit = p?.splits?.reduce((a, s) => a + s.seconds, 0) || 0;
  return (
    <div className="ready-result" id="result">
      <div className="rr-top panel">
        <div className="rr-gauge">
          <TrackGauge score={result.score} verdict={result.verdict} label={result.verdict_label} />
        </div>
        <div className="rr-summary">
          <p className="eyebrow">
            {result.category.name} · {weeksLabel(result.weeks_to_event)} to go
          </p>
          <h3 className={`rr-verdict tone-${verdictTone}`}>{result.verdict_label}</h3>
          <p className="rr-headline">{result.headline}</p>
          {p ? (
            <div className="rr-predict">
              <div>
                <span className="eyebrow">
                  <Timer size={12} weight="bold" style={{ display: "inline", verticalAlign: "-1px" }} /> Estimated finish
                </span>
                <span className="rr-time num">{p.finish_label}</span>
                <span className="small muted">{p.range_label}</span>
              </div>
              {p.pace_label ? (
                <div>
                  <span className="eyebrow">Pace</span>
                  <span className="rr-sub num">{p.pace_label}</span>
                </div>
              ) : null}
              {p.cutoff_label ? (
                <div>
                  <span className="eyebrow">Cutoff</span>
                  <span className="rr-sub num">{p.cutoff_label}</span>
                  <span className={`small ${p.margin_pct < 10 ? "warn-text" : "muted"}`}>
                    {p.margin_pct >= 0 ? `${p.margin_pct}% spare` : `${-p.margin_pct}% over`}
                  </span>
                </div>
              ) : null}
            </div>
          ) : null}
          {p?.splits?.length ? (
            <div className="splits">
              <div className="split-bar">
                {p.splits.map((s, i) => (
                  <span key={s.label} className={`sp sp-${i}`} style={{ flex: s.seconds / totalSplit }} title={`${s.label} ${s.value}`} />
                ))}
              </div>
              <div className="split-legend">
                {p.splits.map((s, i) => (
                  <span key={s.label}>
                    <i className={`sp-${i}`} /> {s.label} <b className="num">{s.value}</b>
                  </span>
                ))}
              </div>
            </div>
          ) : null}
          {p ? <p className="small muted rr-method">{p.method}. An estimate, not a promise.</p> : null}
          {result.day_load ? (
            <p className="small muted rr-method">Typical tournament day: {result.day_load.description}.</p>
          ) : null}
        </div>
      </div>

      <div className="rr-grid">
        <section className="panel panel-pad">
          <h3 className="panel-title" style={{ marginBottom: 14 }}>
            What the score is made of
          </h3>
          <ul className="components">
            {result.components.map((c) => (
              <li key={c.key} className={c.score === null ? "na" : ""}>
                <div className="comp-head">
                  <b>{c.label}</b>
                  <span className="small muted">weight {Math.round(c.weight * 100)}%</span>
                  <span className="num comp-score">{c.score === null ? "n/a" : c.score}</span>
                </div>
                <div className="comp-bar" aria-hidden="true">
                  <span style={{ width: `${c.score ?? 0}%` }} className={c.score >= 80 ? "hi" : c.score >= 50 ? "mid" : "lo"} />
                </div>
                <p className="small muted">{c.detail}</p>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel panel-pad">
          <h3 className="panel-title" style={{ marginBottom: 14 }}>
            Close the gaps
          </h3>
          {result.gaps.length ? (
            <ol className="gaps">
              {result.gaps.map((g) => (
                <li key={g}>{g}</li>
              ))}
            </ol>
          ) : (
            <p className="small muted">Nothing obvious. Stay consistent and arrive rested.</p>
          )}
          {["ready", "nearly"].includes(result.verdict) ? (
            <Link to={`/events/${event.slug}/register?cat=${result.category.id}`} className="btn btn-primary" style={{ marginTop: 18 }}>
              Register for {result.category.name} <ArrowRight size={15} />
            </Link>
          ) : null}
        </section>
      </div>

      {result.plan?.rows?.length ? (
        <section className="panel panel-pad">
          <div className="panel-head">
            <h3 className="panel-title">Your runway to race day</h3>
            <span className="small muted">
              {weeksLabel(result.plan.weeks)}
              {result.plan.target ? ` · peak target ${result.plan.target}` : ""}
            </span>
          </div>
          <div className="plan">
            {result.plan.rows.map((r) => (
              <div key={String(r.week)} className={`plan-row phase-${r.phase.toLowerCase().replace(" ", "-")}`}>
                <span className="plan-week num">W{r.week}</span>
                <span className="plan-date small muted">{formatDate(r.start, { year: false })}</span>
                <span className="plan-phase">{r.phase}</span>
                <span className="plan-target">{r.target}</span>
              </div>
            ))}
          </div>
          <p className="small muted" style={{ marginTop: 12 }}>
            Progressions follow the common "about 10% a week" guideline with an easier week every fourth week, then a
            taper. If something hurts, rest: the plan can wait.
          </p>
        </section>
      ) : null}
    </div>
  );
}

export default function Readiness({ event, categoryId, setCategory, athlete }) {
  const [form, setForm] = useState(null);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get(`/api/events/${event.slug}/readiness-form` + qs({ athlete_id: athlete?.id }))
      .then((f) => {
        setForm(f);
        setValues(f.defaults);
      })
      .catch(setError);
  }, [event.slug, athlete?.id]);

  useEffect(() => {
    setResult(null);
  }, [categoryId]);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setSubmitError(null);
    try {
      const r = await api.post("/api/readiness", {
        event: event.slug,
        category_id: categoryId,
        inputs: values,
        athlete_id: athlete?.id,
      });
      setResult(r);
      requestAnimationFrame(() => document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState error={error} />;
  if (!form) return <Skeleton h={360} r={14} />;

  return (
    <div className="readiness">
      <div className="readiness-intro">
        <p className="eyebrow">Readiness calculator</p>
        <h2 className="section-title">Are you ready for this one?</h2>
        <p className="small muted">
          Tell us where your training is today. We compare it with what {event.sport.name.toLowerCase()} athletes
          typically need for the category you pick, and the weeks left until {formatDate(event.start_date)}.
        </p>
      </div>

      <form className="panel panel-pad readiness-form" onSubmit={submit}>
        <div className="rf-cat">
          <span className="field-label">Category</span>
          <CategoryPills event={event} categoryId={categoryId} setCategory={setCategory} />
        </div>
        {form.has_profile ? (
          <Callout tone="info">Some answers are pre-filled from your {event.sport.name} profile. Adjust them to today.</Callout>
        ) : null}
        <div className="rf-fields">
          {form.fields.map((f) => (
            <Field key={f.id} f={f} value={values[f.id]} onChange={(v) => setValues((s) => ({ ...s, [f.id]: v }))} />
          ))}
        </div>
        {submitError ? <Callout tone="bad" title="Check your answers">{submitError}</Callout> : null}
        <div className="rf-actions">
          <button className="btn btn-ink btn-lg" disabled={busy}>
            {busy ? "Calculating…" : "Check my readiness"}
          </button>
          <span className="small muted">
            <Info size={13} style={{ display: "inline", verticalAlign: "-2px" }} /> General guidance, not medical advice.
          </span>
        </div>
      </form>

      {result ? <Result result={result} event={event} /> : null}
    </div>
  );
}
