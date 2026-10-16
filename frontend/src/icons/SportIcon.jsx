// Sport glyphs drawn on a 24px grid with a 1.6px stroke, so they sit next to
// the Phosphor UI icons without looking borrowed.

const GLYPHS = {
  running: (
    <>
      <circle cx="14.6" cy="4.4" r="1.9" />
      <path d="M13.3 7.8 10.6 13.2" />
      <path d="M7.3 10.6 10.2 8l3.1-.2 2.3 3.2 2.6.4" />
      <path d="M12.7 20.6 13.6 15.6 10.6 13.2 8.4 16.6H5.2" />
    </>
  ),
  "trail-running": (
    <>
      <path d="M2.5 19.5 9 9l3.4 5.3L15.6 10l5.9 9.5Z" />
      <path d="M6.2 19.5c2.3-1.8 5.6-1.1 7.4-3.4" strokeDasharray="1.4 2.1" />
      <circle cx="18.6" cy="5.2" r="1.6" />
    </>
  ),
  cycling: (
    <>
      <circle cx="6" cy="15.5" r="3.9" />
      <circle cx="18" cy="15.5" r="3.9" />
      <path d="M6 15.5h6.4L15.6 9H9.6L6 15.5" />
      <path d="M15.6 9 18 15.5" />
      <path d="M9.6 9 9 6.6M7.8 6.6h2.6" />
      <path d="M15.6 9l-.9-3h2.4" />
    </>
  ),
  swimming: (
    <>
      <circle cx="17.2" cy="7.2" r="1.8" />
      <path d="M4.6 12.6 9.4 9.4l3.2 2.3" />
      <path d="M9.4 9.4 12.2 6l3.2.4" />
      <path d="M2.5 16c1.6 0 1.6-1.2 3.2-1.2s1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3 1.2" />
      <path d="M2.5 20c1.6 0 1.6-1.2 3.2-1.2s1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3.2 1.2 1.6-1.2 3.2-1.2 1.6 1.2 3 1.2" />
    </>
  ),
  triathlon: (
    <>
      <circle cx="8.4" cy="9.6" r="4.6" />
      <circle cx="15.6" cy="9.6" r="4.6" />
      <circle cx="12" cy="15.8" r="4.6" />
    </>
  ),
  "fitness-racing": (
    <>
      <path d="M8.6 10.6V8.4a3.4 3.4 0 0 1 6.8 0v2.2" />
      <path d="M12 9.2a5.9 5.9 0 0 1 4.5 9.7c-.3.4-.8.6-1.3.6H8.8c-.5 0-1-.2-1.3-.6A5.9 5.9 0 0 1 12 9.2Z" />
    </>
  ),
  ocr: (
    <>
      <path d="M2.5 20.2h19" />
      <path d="M5 20.2 12 5l7 15.2" />
      <path d="M7.8 14.2h8.4M9.6 10.2h4.8" />
      <path d="M12 5v15.2" strokeDasharray="1.2 2" />
    </>
  ),
  badminton: (
    <>
      <path d="M9.2 16.4 6.4 4.6M14.8 16.4l2.8-11.8M10.9 16.4l-.6-12.2M13.1 16.4l.6-12.2" />
      <path d="M6.4 4.6c3.7-.8 7.5-.8 11.2 0" />
      <path d="M7.7 10.3h8.6" />
      <path d="M9 16.4h6v1a3 3 0 0 1-6 0Z" />
    </>
  ),
  tennis: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M6.1 5.9a9.2 9.2 0 0 1 0 12.2" />
      <path d="M17.9 5.9a9.2 9.2 0 0 0 0 12.2" />
    </>
  ),
  pickleball: (
    <>
      <rect x="4.2" y="2.6" width="10.4" height="12" rx="4.6" />
      <path d="M8.2 14.6h2.4v5.6a1.2 1.2 0 0 1-2.4 0Z" />
      <circle cx="18.2" cy="17.6" r="2.7" />
      <circle cx="17.5" cy="16.9" r=".45" fill="currentColor" stroke="none" />
      <circle cx="18.9" cy="18.3" r=".45" fill="currentColor" stroke="none" />
    </>
  ),
  football: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 9l2.85 2.07-1.09 3.36h-3.52l-1.09-3.36Z" />
      <path d="M12 9V3.5M14.85 11.07l5.2-1.7M13.76 14.43 17 18.9M10.24 14.43 7 18.9M9.15 11.07l-5.2-1.7" />
    </>
  ),
  "table-tennis": (
    <>
      <path d="M13.1 14.9A6.2 6.2 0 1 1 15.4 12.6l4.2 4.2a1.6 1.6 0 0 1-2.3 2.3Z" fill="currentColor" fillOpacity=".12" />
      <path d="M13.1 14.9l2.3-2.3" />
      <circle cx="19.4" cy="5" r="1.8" />
    </>
  ),
  squash: (
    <>
      <ellipse cx="9.4" cy="9.2" rx="4.6" ry="6.4" transform="rotate(-45 9.4 9.2)" />
      <path d="M12.9 12.9 20 20" strokeWidth="2.2" />
      <path d="M7.4 7.2l4 4M5.9 9.8l3.2 3.2" opacity=".55" />
      <circle cx="18.6" cy="6" r="1.7" />
    </>
  ),
  basketball: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 3.5v17M3.5 12h17" />
      <path d="M6 6c2.5 2.3 3.6 3.9 3.6 6S8.5 15.7 6 18M18 6c-2.5 2.3-3.6 3.9-3.6 6s1.1 3.7 3.6 6" />
    </>
  ),
};

export default function SportIcon({ sport, size = 20, strokeWidth = 1.6, className, title }) {
  const glyph = GLYPHS[sport] || GLYPHS.running;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
    >
      {title ? <title>{title}</title> : null}
      {glyph}
    </svg>
  );
}

export const SPORT_SLUGS = Object.keys(GLYPHS);
