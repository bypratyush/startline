import { Link } from "react-router";

// The mark: a 400 m track seen from above, the lane surface in pitch green and
// one white start line painted across the home straight.
export function LogoMark({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className="logo-mark">
      <path d="M10 9.2h12a6.8 6.8 0 0 1 0 13.6H10a6.8 6.8 0 0 1 0-13.6Z" fill="none" stroke="var(--accent)" strokeWidth="5" />
      <path d="M10 9.2h12a6.8 6.8 0 0 1 0 13.6H10a6.8 6.8 0 0 1 0-13.6Z" fill="none" stroke="#fff" strokeWidth=".75" opacity=".9" />
      <path d="M17.2 18.6v8.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export default function Logo() {
  return (
    <Link to="/" className="logo" aria-label="StartLine home">
      <LogoMark />
      <span className="logo-word">StartLine</span>
    </Link>
  );
}
