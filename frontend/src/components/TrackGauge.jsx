// Readiness score drawn as a lap of a 400 m track, run anticlockwise from the
// start line on the home straight.
const STADIUM = "M110 130H150A60 60 0 0 0 150 10H70A60 60 0 0 0 70 130Z";
const OUTER = "M110 141H150A71 71 0 0 0 150 -1H70A71 71 0 0 0 70 141Z";
const INNER = "M110 119H150A49 49 0 0 0 150 21H70A49 49 0 0 0 70 119Z";

const TONE = {
  ready: "var(--good)",
  nearly: "var(--info)",
  build: "var(--warn)",
  "not-this-one": "var(--bad)",
};

export default function TrackGauge({ score, verdict, label, size = 260 }) {
  const color = TONE[verdict] || "var(--ink)";
  return (
    <div className="track-gauge" style={{ width: size, "--tone": color }}>
      <svg viewBox="-6 -6 232 152" role="img" aria-label={`Readiness ${score} out of 100: ${label}`}>
        {/* the track surface, its outer and inner edges, and a dashed lane line */}
        <path d={STADIUM} fill="none" stroke="var(--paper-2)" strokeWidth="22" />
        <path d={OUTER} fill="none" stroke="var(--line-2)" strokeWidth="1" />
        <path d={INNER} fill="none" stroke="var(--line-2)" strokeWidth="1" />
        <path d={STADIUM} fill="none" stroke="var(--surface)" strokeWidth=".8" strokeDasharray="3 4" opacity=".9" />
        {/* progress */}
        <path
          className="tg-progress"
          d={STADIUM}
          fill="none"
          stroke={color}
          strokeWidth="11"
          strokeLinecap="round"
          pathLength="100"
          strokeDasharray={`${Math.max(0.5, score)} 100`}
        />
        {/* start line */}
        <path d="M110 118v24" stroke="var(--ink)" strokeWidth="2.4" />
        <text x="110" y="66" textAnchor="middle" className="tg-score">
          {score}
        </text>
        <text x="110" y="88" textAnchor="middle" className="tg-label">
          {label.toUpperCase()}
        </text>
      </svg>
    </div>
  );
}
