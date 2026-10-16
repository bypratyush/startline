import { CheckCircle, Info, WarningCircle } from "@phosphor-icons/react";
import SportIcon from "../icons/SportIcon.jsx";
import { dateParts, sportVar } from "../lib/format.js";

export function SportTag({ sport, size = "md", withName = true }) {
  return (
    <span className={`sport-tag sport-tag-${size}`} style={{ "--c": sportVar(sport.slug) }}>
      <SportIcon sport={sport.slug} size={size === "sm" ? 14 : 16} strokeWidth={1.8} />
      {withName ? <span>{sport.name}</span> : null}
    </span>
  );
}

export function DateBlock({ iso, status, compact }) {
  const p = dateParts(iso);
  return (
    <div className={`date-block${compact ? " compact" : ""}${status === "expected" ? " expected" : ""}`}>
      <span className="db-month">{p.month}</span>
      <span className="db-day num">{p.day}</span>
      <span className="db-week">{p.weekday}</span>
    </div>
  );
}

const TIER_LABEL = { great: "Great match", good: "Good match", stretch: "Stretch" };

// A small lap: the arc fills with the match score.
export function MatchRing({ match, size = 34, label = true }) {
  if (!match) return null;
  const circ = 2 * Math.PI * 15;
  return (
    <span className={`match-ring tier-${match.tier}`} title={`${TIER_LABEL[match.tier]}: ${match.score} of 100`}>
      <svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true">
        <circle cx="18" cy="18" r="15" fill="none" stroke="var(--line)" strokeWidth="2" />
        <circle
          cx="18"
          cy="18"
          r="15"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="butt"
          strokeDasharray={`${(match.score / 100) * circ} ${circ}`}
          transform="rotate(-90 18 18)"
        />
        <text x="18" y="22.6" textAnchor="middle" className="mr-num">
          {match.score}
        </text>
      </svg>
      {label ? <span className="mr-label">{TIER_LABEL[match.tier]}</span> : null}
    </span>
  );
}

export function MatchPill({ match }) {
  return <MatchRing match={match} size={30} />;
}

export function Toggle({ checked, onChange, label, hint, id }) {
  return (
    <label className="toggle" htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="toggle-track" aria-hidden="true">
        <span className="toggle-thumb" />
      </span>
      <span className="toggle-text">
        <span>{label}</span>
        {hint ? <span className="toggle-hint">{hint}</span> : null}
      </span>
    </label>
  );
}

export function Segmented({ options, value, onChange, label, size }) {
  return (
    <div className={`segmented${size ? ` segmented-${size}` : ""}`} role="radiogroup" aria-label={label}>
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? "on" : ""}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Select({ value, onChange, children, label, className = "", icon }) {
  return (
    <label className={`select ${className}`}>
      {icon ? <span className="select-icon">{icon}</span> : null}
      <span className="visually-hidden">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        {children}
      </select>
      <svg className="select-caret" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
        <path d="M3 4.5 6 7.5 9 4.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    </label>
  );
}

export function Badge({ tone = "neutral", children, title }) {
  return (
    <span className={`badge badge-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function Callout({ tone = "info", title, children }) {
  const Icon = tone === "good" ? CheckCircle : tone === "info" ? Info : WarningCircle;
  return (
    <div className={`callout callout-${tone}`}>
      <Icon size={18} weight="bold" />
      <div>
        {title ? <strong>{title}</strong> : null}
        {children ? <div className="callout-body">{children}</div> : null}
      </div>
    </div>
  );
}

export function Skeleton({ h = 16, w = "100%", r = 6, style }) {
  return <span className="skeleton" style={{ height: h, width: w, borderRadius: r, ...style }} />;
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty">
      <svg width="96" height="40" viewBox="0 0 96 40" aria-hidden="true" className="empty-art">
        <path d="M6 34h84M6 22h84M6 10h84" stroke="var(--line-2)" strokeWidth="1.5" strokeDasharray="10 7" />
        <rect x="14" y="6" width="3" height="32" rx="1.2" fill="var(--accent)" />
      </svg>
      <h3>{title}</h3>
      {children ? <p className="muted">{children}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({ error, retry }) {
  return (
    <div className="empty">
      <WarningCircle size={32} color="var(--bad)" />
      <h3>Could not reach the StartLine API</h3>
      <p className="muted">{error?.message || "The backend did not respond."} Check that the backend is running.</p>
      {retry ? (
        <button className="btn btn-sm" onClick={retry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

// Subtle sport-specific line art used behind headers.
export function SportPattern({ family, slug }) {
  const id = `pat-${slug}`;
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1 };
  let art;
  if (family === "run" && slug === "trail-running") {
    art = (
      <g {...common}>
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <path key={i} d={`M-20 ${150 - i * 18}c80-${30 + i * 4} 140 ${20 - i * 3} 220-${18 + i * 2}s150 ${12 + i} 260-${16 + i * 3}`} />
        ))}
      </g>
    );
  } else if (family === "run") {
    // the bend of a running track: lanes run straight, then curve around
    const lanes = [0, 1, 2, 3, 4, 5, 6];
    art = (
      <g {...common}>
        {lanes.map((i) => {
          const r = 54 + i * 20;
          return <path key={i} d={`M-10 ${210 - r}H290A${r} ${r} 0 0 1 ${290 + r} 210`} />;
        })}
      </g>
    );
  } else if (family === "swim") {
    art = (
      <g {...common}>
        {[0, 1, 2, 3, 4].map((i) => (
          <path key={i} d={`M-10 ${36 + i * 28}H420`} strokeDasharray="2 6" strokeWidth="2" strokeLinecap="round" />
        ))}
      </g>
    );
  } else if (family === "ride") {
    art = (
      <g {...common}>
        <path d="M-10 120C80 40 200 160 300 80s120-40 140-30" strokeWidth="1.2" />
        <path d="M-10 120C80 40 200 160 300 80s120-40 140-30" strokeDasharray="10 10" transform="translate(0 16)" />
        <path d="M-10 120C80 40 200 160 300 80s120-40 140-30" transform="translate(0 32)" />
      </g>
    );
  } else if (family === "tri") {
    art = (
      <g {...common}>
        <path d="M-10 60c20-8 40 8 60 0s40-8 60 0 40 8 60 0" />
        <path d="M-10 74c20-8 40 8 60 0s40-8 60 0 40 8 60 0" />
        <circle cx="250" cy="70" r="34" />
        <circle cx="250" cy="70" r="6" />
        <path d="M330 140c10-30 30-70 90-90" strokeDasharray="8 8" />
      </g>
    );
  } else if (family === "court") {
    art = (
      <g {...common}>
        <rect x="40" y="20" width="340" height="150" />
        <path d="M210 20v150M40 60h340M40 130h340M125 60v70M295 60v70" />
      </g>
    );
  } else if (family === "team") {
    art = (
      <g {...common}>
        <rect x="20" y="16" width="380" height="160" />
        <path d="M210 16v160" />
        <circle cx="210" cy="96" r="34" />
        <rect x="20" y="56" width="50" height="80" />
        <rect x="350" y="56" width="50" height="80" />
      </g>
    );
  } else {
    art = (
      <g {...common}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <path key={i} d={`M${i * 50 - 40} 180l60-160`} />
        ))}
      </g>
    );
  }
  return (
    <svg className="sport-pattern" viewBox="0 0 420 190" preserveAspectRatio="xMaxYMid slice" aria-hidden="true" id={id}>
      {art}
    </svg>
  );
}
