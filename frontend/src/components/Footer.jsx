import { LogoMark } from "./Logo.jsx";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="row" style={{ "--gap": "10px" }}>
          <LogoMark size={22} />
          <span className="small muted">
            StartLine lists real events from organiser websites. Dates marked <b>Expected</b> follow the event's usual
            weekend and are not yet confirmed: always check the official site before you travel.
          </span>
        </div>
        <span className="small muted footer-meta">Made for Indian amateur athletes · Tier 1 and Tier 2 cities</span>
      </div>
    </footer>
  );
}
