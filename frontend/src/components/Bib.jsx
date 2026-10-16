import SportIcon from "../icons/SportIcon.jsx";
import { formatDate, sportVar } from "../lib/format.js";

// A race bib, safety-pin holes and all.
export default function Bib({ registration, compact }) {
  const r = registration;
  const cancelled = r.status === "cancelled";
  return (
    <div
      className={`bib${compact ? " compact" : ""}${cancelled ? " cancelled" : ""}`}
      style={{ "--c": sportVar(r.event.sport.slug) }}
    >
      <span className="bib-hole h1" />
      <span className="bib-hole h2" />
      <span className="bib-hole h3" />
      <span className="bib-hole h4" />
      <div className="bib-band">
        <SportIcon sport={r.event.sport.slug} size={14} strokeWidth={2} />
        <span>{r.event.name}</span>
      </div>
      <div className="bib-number num">{r.bib_number}</div>
      <div className="bib-name">{r.full_name}</div>
      <div className="bib-foot">
        <span>{r.category.name}</span>
        <span>{formatDate(r.event.start_date)}</span>
        <span className="bib-code">{r.code}</span>
      </div>
      {cancelled ? <span className="bib-stamp">Cancelled</span> : null}
    </div>
  );
}
