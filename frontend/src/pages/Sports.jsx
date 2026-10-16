import { ArrowRight } from "@phosphor-icons/react";
import { Link } from "react-router";
import { Skeleton } from "../components/ui.jsx";
import SportIcon from "../icons/SportIcon.jsx";
import { useAthlete } from "../lib/athlete.jsx";
import { sportVar } from "../lib/format.js";

const FAMILY_LABEL = {
  run: "Endurance",
  ride: "Endurance",
  swim: "Endurance",
  tri: "Multisport",
  hyrox: "Fitness",
  ocr: "Fitness",
  court: "Racquet",
  team: "Team",
};

export default function Sports() {
  const { sports, athlete, catalogLoaded } = useAthlete();
  const mine = new Set(athlete?.sports.map((s) => s.sport.slug) || []);
  return (
    <div className="container page">
      <header className="page-head">
        <p className="eyebrow">{sports.length} sports</p>
        <h1 className="page-title">Every sport, explained</h1>
        <p className="lede">
          What each sport looks like for amateurs in India, how we decide your level, which formats suit you, and the
          upcoming events to aim for.
        </p>
      </header>
      <div className="sports-grid">
        {!catalogLoaded
          ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={190} r={14} />)
          : sports.map((s) => (
              <Link key={s.slug} to={`/sports/${s.slug}`} className="sport-card" style={{ "--c": sportVar(s.slug) }}>
                <div className="sc-top">
                  <span className="sc-icon">
                    <SportIcon sport={s.slug} size={28} strokeWidth={1.6} />
                  </span>
                  <span className="eyebrow">{FAMILY_LABEL[s.family]}</span>
                </div>
                <h2 className="sc-name">{s.name}</h2>
                <p className="sc-tag">{s.tagline}</p>
                <p className="small muted sc-desc">{s.description}</p>
                <div className="sc-foot">
                  <span className="num sc-count">{s.events}</span>
                  <span className="small muted">upcoming events</span>
                  {mine.has(s.slug) ? <span className="badge badge-accent">Your sport</span> : null}
                  <ArrowRight size={16} className="sc-arrow" />
                </div>
              </Link>
            ))}
      </div>
    </div>
  );
}
