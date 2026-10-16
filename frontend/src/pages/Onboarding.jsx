import { ArrowLeft, ArrowRight, Check, Crosshair } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { Callout, Skeleton, Toggle } from "../components/ui.jsx";
import SportIcon from "../icons/SportIcon.jsx";
import { useAthlete } from "../lib/athlete.jsx";
import { sportVar } from "../lib/format.js";

function Progress({ steps, current }) {
  return (
    <ol className="ob-progress" aria-label="Progress">
      {steps.map((s, i) => (
        <li key={s.key} className={i < current ? "done" : i === current ? "now" : ""} style={s.color ? { "--c": s.color } : null}>
          <span className="obp-lane" />
          <span className="obp-label">
            {s.sport ? <SportIcon sport={s.sport} size={14} strokeWidth={2} /> : null}
            {s.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Question({ q, value, onChange, color }) {
  return (
    <fieldset className="ob-q">
      <legend>
        <span className="ob-q-prompt">{q.prompt}</span>
        {q.help ? <span className="ob-q-help">{q.help}</span> : null}
      </legend>
      <div className="choices">
        {q.options.map((o) => (
          <button
            type="button"
            key={o.value}
            className={`choice${value === o.value ? " on" : ""}`}
            style={{ "--c": color }}
            aria-pressed={value === o.value}
            onClick={() => onChange(o.value)}
          >
            <span className="choice-label">{o.label}</span>
            {o.hint ? <span className="choice-hint">{o.hint}</span> : null}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

export default function Onboarding({ edit = false }) {
  const { athlete, loading, sports, cities, save, signOut, catalogLoaded } = useAthlete();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [city, setCity] = useState("");
  const [recs, setRecs] = useState(true);
  const [chosen, setChosen] = useState([]);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);

  // editing: start from the stored profile
  useEffect(() => {
    if (!athlete) return;
    setName(athlete.name);
    setEmail(athlete.email || "");
    setCity(athlete.city?.slug || "");
    setRecs(athlete.recommendations_enabled);
    setChosen(athlete.sports.map((s) => s.sport.slug));
    setAnswers(Object.fromEntries(athlete.sports.map((s) => [s.sport.slug, s.answers])));
  }, [athlete]);

  const bySlug = useMemo(() => Object.fromEntries(sports.map((s) => [s.slug, s])), [sports]);
  const chosenSports = chosen.map((s) => bySlug[s]).filter(Boolean);
  const steps = [
    { key: "you", label: "You" },
    { key: "sports", label: "Sports" },
    ...chosenSports.map((s) => ({ key: s.slug, label: s.name, sport: s.slug, color: sportVar(s.slug) })),
  ];
  const sportStep = step >= 2 ? chosenSports[step - 2] : null;

  if (loading || !catalogLoaded) {
    return (
      <div className="container ob">
        <Skeleton h={30} w="50%" />
        <Skeleton h={300} style={{ marginTop: 24 }} r={14} />
      </div>
    );
  }

  if (!edit && athlete && !saved) {
    return (
      <div className="container ob">
        <div className="empty">
          <h3>You already have a profile</h3>
          <p className="muted">Edit it to change your sports, answers or city.</p>
          <Link to="/profile" className="btn btn-ink btn-sm">
            Edit profile
          </Link>
        </div>
      </div>
    );
  }

  function toggleSport(slug) {
    setChosen((c) => (c.includes(slug) ? c.filter((x) => x !== slug) : [...c, slug]));
  }

  function setAnswer(sport, qid, value) {
    setAnswers((a) => ({ ...a, [sport]: { ...(a[sport] || {}), [qid]: value } }));
  }

  const sportComplete = (s) => s.questions.every((q) => answers[s.slug]?.[q.id]);
  const canNext =
    step === 0 ? name.trim().length > 0 && city : step === 1 ? chosen.length > 0 : sportStep ? sportComplete(sportStep) : false;
  const isLast = step === steps.length - 1 && step >= 2;

  function locate() {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition((pos) => {
      const rad = (d) => (d * Math.PI) / 180;
      let best = null;
      let bestD = Infinity;
      for (const c of cities) {
        const a =
          Math.sin(rad(c.lat - pos.coords.latitude) / 2) ** 2 +
          Math.cos(rad(pos.coords.latitude)) * Math.cos(rad(c.lat)) * Math.sin(rad(c.lon - pos.coords.longitude) / 2) ** 2;
        const d = 12742 * Math.asin(Math.sqrt(a));
        if (d < bestD) {
          bestD = d;
          best = c;
        }
      }
      if (best) setCity(best.slug);
    });
  }

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      const body = {
        name: name.trim(),
        email: email.trim() || null,
        city,
        recommendations_enabled: recs,
        sports: chosen.map((slug) => ({ sport: slug, answers: answers[slug] || {} })),
      };
      const a = await save(body);
      setSaved(a);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (saved) {
    const next = params.get("next");
    return (
      <div className="container ob ob-done">
        <div className="ob-done-mark" aria-hidden="true">
          <Check size={30} weight="bold" />
        </div>
        <p className="eyebrow">Profile {edit ? "updated" : "ready"}</p>
        <h1 className="ob-title">You're on the start line, {saved.name.split(" ")[0]}.</h1>
        <p className="lede">Here's how we read your answers. Recommendations use these levels and your capacities.</p>
        <ul className="ob-levels">
          {saved.sports.map((s) => (
            <li key={s.sport.slug} style={{ "--c": sportVar(s.sport.slug) }}>
              <SportIcon sport={s.sport.slug} size={22} strokeWidth={1.7} />
              <div>
                <b>{bySlug[s.sport.slug]?.name || s.sport.name}</b>
                <span className="small muted">{s.labels.filter((l) => l.question !== "Level").map((l) => l.answer).join(" · ")}</span>
              </div>
              <span className={`lvl lvl-${s.level}`}>{s.level}</span>
            </li>
          ))}
        </ul>
        <div className="row" style={{ "--gap": "10px", flexWrap: "wrap" }}>
          <button className="btn btn-primary btn-lg" onClick={() => navigate(next || "/")}>
            {next ? "Continue" : "See events picked for you"} <ArrowRight size={16} />
          </button>
          <Link className="btn btn-lg" to="/season">
            My season
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container ob">
      <div className="ob-head">
        <p className="eyebrow">{edit ? "Edit your profile" : "Build your profile"}</p>
        <Progress steps={steps} current={step} />
      </div>

      <div className="ob-card panel">
        {step === 0 ? (
          <div className="ob-step">
            <h1 className="ob-title">Let's set your start line.</h1>
            <p className="lede">Your city sets distances and what counts as nearby. No password, nothing to verify.</p>
            <div className="form-grid" style={{ marginTop: 24 }}>
              <label className="field">
                <span className="field-label">Your name</span>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" autoFocus />
              </label>
              <label className="field">
                <span className="field-label">
                  Email <span className="opt">optional, prefills registrations</span>
                </span>
                <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
              </label>
              <label className="field">
                <span className="field-label">Home city</span>
                <select value={city} onChange={(e) => setCity(e.target.value)}>
                  <option value="">Choose your city</option>
                  <optgroup label="Tier 1">
                    {cities
                      .filter((c) => c.tier === 1)
                      .map((c) => (
                        <option key={c.slug} value={c.slug}>
                          {c.name}
                        </option>
                      ))}
                  </optgroup>
                  <optgroup label="Tier 2">
                    {cities
                      .filter((c) => c.tier === 2)
                      .map((c) => (
                        <option key={c.slug} value={c.slug}>
                          {c.name}
                        </option>
                      ))}
                  </optgroup>
                </select>
              </label>
              <div className="field" style={{ justifyContent: "flex-end" }}>
                <button type="button" className="btn" onClick={locate}>
                  <Crosshair size={16} weight="bold" /> Use my location
                </button>
              </div>
            </div>
            <div style={{ marginTop: 22 }}>
              <Toggle
                id="ob-recs"
                checked={recs}
                onChange={setRecs}
                label="Show recommendations"
                hint="Rank events by how well they fit you. You can switch this off any time."
              />
            </div>
          </div>
        ) : null}

        {step === 1 ? (
          <div className="ob-step">
            <h1 className="ob-title">What do you play?</h1>
            <p className="lede">Pick one or several. Each sport asks two or three quick questions.</p>
            <div className="sport-grid">
              {sports.map((s) => {
                const on = chosen.includes(s.slug);
                return (
                  <button
                    key={s.slug}
                    type="button"
                    className={`sport-tile${on ? " on" : ""}`}
                    style={{ "--c": sportVar(s.slug) }}
                    onClick={() => toggleSport(s.slug)}
                    aria-pressed={on}
                  >
                    <span className="st-icon">
                      <SportIcon sport={s.slug} size={26} strokeWidth={1.6} />
                    </span>
                    <span className="st-name">{s.name}</span>
                    <span className="st-tag small muted">{s.tagline}</span>
                    <span className="st-count small">{s.events} events</span>
                    <span className="st-check" aria-hidden="true">
                      <Check size={12} weight="bold" />
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ) : null}

        {sportStep ? (
          <div className="ob-step" style={{ "--c": sportVar(sportStep.slug) }}>
            <div className="ob-sport-head">
              <span className="ob-sport-icon">
                <SportIcon sport={sportStep.slug} size={28} strokeWidth={1.6} />
              </span>
              <div>
                <p className="eyebrow">
                  Sport {step - 1} of {chosenSports.length}
                </p>
                <h1 className="ob-title">{sportStep.name}</h1>
              </div>
            </div>
            <p className="lede">{sportStep.description}</p>
            {sportStep.questions.map((q) => (
              <Question
                key={q.id}
                q={q}
                value={answers[sportStep.slug]?.[q.id]}
                onChange={(v) => setAnswer(sportStep.slug, q.id, v)}
                color={sportVar(sportStep.slug)}
              />
            ))}
          </div>
        ) : null}

        {error ? <Callout tone="bad" title="Could not save your profile">{error}</Callout> : null}

        <div className="ob-nav">
          {step > 0 ? (
            <button className="btn btn-ghost" onClick={() => setStep((s) => s - 1)}>
              <ArrowLeft size={16} /> Back
            </button>
          ) : edit ? (
            <button
              className="btn btn-ghost"
              onClick={() => {
                signOut();
                navigate("/");
              }}
            >
              Sign out of this profile
            </button>
          ) : (
            <span />
          )}
          {isLast ? (
            <button className="btn btn-primary btn-lg" disabled={!canNext || busy} onClick={finish}>
              {busy ? "Saving…" : edit ? "Save profile" : "Finish"} <Check size={16} weight="bold" />
            </button>
          ) : (
            <button className="btn btn-ink btn-lg" disabled={!canNext} onClick={() => setStep((s) => s + 1)}>
              {step === 1 && chosen.length ? `Next: ${chosenSports[0]?.name}` : "Next"} <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
