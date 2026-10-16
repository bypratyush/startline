import { ArrowSquareOut, CalendarPlus, CheckCircle, ListChecks } from "@phosphor-icons/react";
import { useEffect, useState } from "react";
import { Link } from "react-router";
import Bib from "../../components/Bib.jsx";
import { Callout, Segmented } from "../../components/ui.jsx";
import { api } from "../../lib/api.js";
import { formatDate, inr, km, LEVEL_LABEL, minutesLabel } from "../../lib/format.js";

const SIZES = ["XS", "S", "M", "L", "XL", "XXL"].map((s) => ({ value: s, label: s }));
const GENDERS = [
  { value: "female", label: "Female" },
  { value: "male", label: "Male" },
  { value: "non-binary", label: "Non-binary" },
  { value: "prefer-not-to-say", label: "Prefer not to say" },
];
const BLOOD = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

const isDoubles = (c) => /doubles|mixed|pair/i.test(c.name);
const isTeam = (c, fam) => fam === "team" || /relay|team/i.test(c.name);

export default function Register({ event, categoryId, setCategory, athlete }) {
  const [existing, setExisting] = useState([]);
  const [done, setDone] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [f, setF] = useState({
    full_name: athlete?.name || "",
    email: athlete?.email || "",
    phone: "",
    gender: "",
    date_of_birth: "",
    tshirt_size: "",
    blood_group: "",
    emergency_name: "",
    emergency_phone: "",
    team_name: "",
    partner_name: "",
    medical_declaration: false,
  });

  useEffect(() => {
    if (!athlete) return;
    api
      .get(`/api/athletes/${athlete.id}/registrations`)
      .then((rows) => setExisting(rows.filter((r) => r.event.slug === event.slug && r.status === "confirmed")))
      .catch(() => {});
  }, [athlete, event.slug, done]);

  if (!athlete) {
    return (
      <div className="register-gate panel panel-pad">
        <h2 className="section-title">Build your profile to register</h2>
        <p className="small muted" style={{ margin: "8px 0 16px", maxWidth: "54ch" }}>
          Registrations are tied to your StartLine profile so they appear in My season, with recovery warnings and
          your bib. It takes under a minute.
        </p>
        <Link to={`/start?next=/events/${event.slug}/register`} className="btn btn-primary">
          Build your profile
        </Link>
      </div>
    );
  }

  const cat = event.categories.find((c) => c.id === categoryId);
  const fam = event.sport.family;
  const endurance = !["court", "team"].includes(fam);
  const closed = event.registration_status === "closed";
  const set = (k) => (v) => setF((s) => ({ ...s, [k]: v }));

  async function submit(e) {
    e.preventDefault();
    setErr(null);
    if (!f.gender) return setErr("Please choose a gender option.");
    setBusy(true);
    try {
      const body = {
        ...f,
        athlete_id: athlete.id,
        event: event.slug,
        category_id: categoryId,
        tshirt_size: f.tshirt_size || null,
        blood_group: f.blood_group || null,
        email: f.email.trim(),
        team_name: f.team_name || null,
        partner_name: f.partner_name || null,
      };
      const reg = await api.post("/api/registrations", body);
      setDone(reg);
      window.scrollTo({ top: document.querySelector(".ev-tabs")?.offsetTop - 70 || 0, behavior: "smooth" });
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="register-done">
        <div className="rd-bib">
          <Bib registration={done} />
        </div>
        <div className="rd-copy">
          <p className="eyebrow">
            <CheckCircle size={14} weight="fill" color="var(--good)" style={{ display: "inline", verticalAlign: "-2px" }} />{" "}
            You're on the start list
          </p>
          <h2 className="section-title">See you at the start line, {done.full_name.split(" ")[0]}.</h2>
          <p className="small muted">
            Bib <b className="num ink">{done.bib_number}</b> · {done.category.name} · {formatDate(done.event.start_date, { weekday: true })}
            {done.category.start_time ? ` at ${done.category.start_time}` : ""}. Your confirmation code is{" "}
            <b className="ink">{done.code}</b>.
          </p>
          <div className="rd-actions">
            <a className="btn btn-ink" href={`/api/events/${event.slug}/calendar.ics?category_id=${done.category.id}`}>
              <CalendarPlus size={16} /> Add to calendar
            </a>
            <Link className="btn" to={`/events/${event.slug}/guide?cat=${done.category.id}`}>
              <ListChecks size={16} /> Open the event guide
            </Link>
            <Link className="btn btn-ghost" to="/season">
              My season
            </Link>
          </div>
          {event.official_url ? (
            <Callout tone="info" title="Confirm with the organiser">
              StartLine keeps your place in your season plan. Timing chips, bib collection and payment are handled by the
              organiser:{" "}
              <a className="link" href={event.registration.url || event.official_url} target="_blank" rel="noreferrer">
                complete the official entry <ArrowSquareOut size={12} style={{ display: "inline" }} />
              </a>
            </Callout>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <form className="register" onSubmit={submit}>
      <div className="reg-main">
        {closed ? (
          <Callout tone="warn" title="Registration is closed for this edition">
            The organiser has closed entries. Save the event to your season to catch the next one.
          </Callout>
        ) : null}
        {existing.length ? (
          <Callout tone="good" title="You're already registered here">
            {existing.map((r) => `${r.category.name} (bib ${r.bib_number})`).join(", ")}. You can add another category.
          </Callout>
        ) : null}

        <section className="panel panel-pad">
          <h3 className="panel-title">1 · Choose your category</h3>
          <div className="reg-cats">
            {event.categories.map((c) => (
              <button
                type="button"
                key={c.id}
                className={`reg-cat${c.id === categoryId ? " on" : ""}`}
                onClick={() => setCategory(c.id)}
                aria-pressed={c.id === categoryId}
              >
                <span className="rc-name">{c.name}</span>
                <span className="rc-meta small muted">
                  {[
                    c.distance_km && endurance ? km(c.distance_km) : null,
                    c.start_time ? `start ${c.start_time}` : null,
                    c.cutoff_minutes ? `cutoff ${minutesLabel(c.cutoff_minutes)}` : null,
                    LEVEL_LABEL[c.level],
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
                <span className="rc-fee num">{c.fee_inr ? inr(c.fee_inr) : "Fee TBA"}</span>
              </button>
            ))}
          </div>
          {cat?.eligibility ? <p className="small muted" style={{ marginTop: 10 }}>Eligibility: {cat.eligibility}</p> : null}
        </section>

        <section className="panel panel-pad">
          <h3 className="panel-title">2 · Your details</h3>
          <div className="form-grid">
            <label className="field span-2">
              <span className="field-label">Full name (as on your ID)</span>
              <input className="input" value={f.full_name} onChange={(e) => set("full_name")(e.target.value)} required minLength={2} autoComplete="name" />
            </label>
            <label className="field">
              <span className="field-label">Email</span>
              <input className="input" type="email" value={f.email} onChange={(e) => set("email")(e.target.value)} required autoComplete="email" />
            </label>
            <label className="field">
              <span className="field-label">Mobile</span>
              <input
                className="input"
                inputMode="tel"
                placeholder="98xxxxxxxx"
                value={f.phone}
                onChange={(e) => set("phone")(e.target.value)}
                required
                autoComplete="tel"
              />
            </label>
            <label className="field">
              <span className="field-label">Date of birth</span>
              <input className="input" type="date" value={f.date_of_birth} onChange={(e) => set("date_of_birth")(e.target.value)} required />
              {cat?.min_age ? <span className="field-hint">Minimum age {cat.min_age} on event day</span> : null}
            </label>
            <div className="field">
              <span className="field-label">Gender</span>
              <Segmented options={GENDERS} value={f.gender} onChange={set("gender")} label="Gender" size="sm" />
            </div>
            {endurance ? (
              <div className="field">
                <span className="field-label">
                  T-shirt size <span className="opt">optional</span>
                </span>
                <Segmented options={SIZES} value={f.tshirt_size} onChange={set("tshirt_size")} label="T-shirt size" size="sm" />
              </div>
            ) : null}
            <label className="field">
              <span className="field-label">
                Blood group <span className="opt">recommended</span>
              </span>
              <select value={f.blood_group} onChange={(e) => set("blood_group")(e.target.value)}>
                <option value="">Select</option>
                {BLOOD.map((b) => (
                  <option key={b}>{b}</option>
                ))}
              </select>
            </label>
            {cat && isDoubles(cat) ? (
              <label className="field">
                <span className="field-label">Partner's name</span>
                <input className="input" value={f.partner_name} onChange={(e) => set("partner_name")(e.target.value)} required />
              </label>
            ) : null}
            {cat && isTeam(cat, fam) ? (
              <label className="field">
                <span className="field-label">Team name</span>
                <input className="input" value={f.team_name} onChange={(e) => set("team_name")(e.target.value)} required />
              </label>
            ) : null}
          </div>
        </section>

        <section className="panel panel-pad">
          <h3 className="panel-title">3 · Emergency contact</h3>
          <div className="form-grid">
            <label className="field">
              <span className="field-label">Name</span>
              <input className="input" value={f.emergency_name} onChange={(e) => set("emergency_name")(e.target.value)} required minLength={2} />
            </label>
            <label className="field">
              <span className="field-label">Mobile</span>
              <input className="input" inputMode="tel" value={f.emergency_phone} onChange={(e) => set("emergency_phone")(e.target.value)} required />
            </label>
          </div>
          <label className="checkbox" style={{ marginTop: 16 }}>
            <input type="checkbox" checked={f.medical_declaration} onChange={(e) => set("medical_declaration")(e.target.checked)} required />
            <span>
              I am medically fit to take part, I have trained for this category, and I will follow the organiser's
              safety rules on the day.
            </span>
          </label>
        </section>
      </div>

      <aside className="reg-aside">
        <div className="panel panel-pad reg-summary">
          <p className="eyebrow">Your entry</p>
          <h3 className="rs-event">{event.name}</h3>
          <dl className="rs-list">
            <div>
              <dt>Category</dt>
              <dd>{cat?.name || "-"}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{formatDate(event.start_date, { weekday: true })}</dd>
            </div>
            <div>
              <dt>Start</dt>
              <dd className="num">{cat?.start_time || "TBA"}</dd>
            </div>
            <div>
              <dt>Venue</dt>
              <dd>{event.city.name}</dd>
            </div>
            <div className="rs-total">
              <dt>Entry fee</dt>
              <dd className="num">{cat?.fee_inr ? inr(cat.fee_inr) : "Set by organiser"}</dd>
            </div>
          </dl>
          {err ? <Callout tone="bad" title="Not registered yet">{err}</Callout> : null}
          <button className="btn btn-primary btn-lg rs-submit" disabled={busy || closed || !categoryId}>
            {busy ? "Registering…" : "Confirm registration"}
          </button>
          <p className="small muted">You will get a bib number and confirmation code right away.</p>
        </div>
      </aside>
    </form>
  );
}
