const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function parseDate(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function dateParts(iso) {
  const d = parseDate(iso);
  return { day: d.getDate(), month: MONTHS[d.getMonth()], weekday: DAYS[d.getDay()], year: d.getFullYear() };
}

export function formatDate(iso, { year = true, weekday = false } = {}) {
  if (!iso) return "";
  const d = parseDate(iso);
  const base = `${d.getDate()} ${MONTHS[d.getMonth()]}${year ? ` ${d.getFullYear()}` : ""}`;
  return weekday ? `${DAYS[d.getDay()]}, ${base}` : base;
}

export function formatRange(start, end) {
  if (!end || start === end) return formatDate(start, { weekday: true });
  const a = parseDate(start);
  const b = parseDate(end);
  if (a.getMonth() === b.getMonth()) return `${a.getDate()} to ${b.getDate()} ${MONTHS[b.getMonth()]} ${b.getFullYear()}`;
  return `${formatDate(start, { year: false })} to ${formatDate(end)}`;
}

export function monthLabel(key) {
  const [y, m] = key.split("-").map(Number);
  return { month: MONTHS_LONG[m - 1], short: MONTHS[m - 1], year: y };
}

export function inr(n) {
  if (n === null || n === undefined) return null;
  return "₹" + Number(n).toLocaleString("en-IN");
}

export function feeRange(min, max) {
  if (min === null || min === undefined) return null;
  if (!max || max === min) return inr(min);
  return `${inr(min)} to ${inr(max)}`;
}

export function km(n) {
  if (n === null || n === undefined) return null;
  if (n < 1) return `${Math.round(n * 1000)} m`;
  return `${Number.isInteger(n) ? n : Number(n.toFixed(2))} km`;
}

// "21.1K", "42.2K", "750 m", "BRM 200"
export function distanceTag(cat, family) {
  if (family === "tri" && cat.swim_km) return null;
  const d = cat.distance_km;
  if (!d) return null;
  if (d < 1) return `${Math.round(d * 1000)} m`;
  if (family === "swim") return `${Number(d.toFixed(2))} km`;
  return `${Number(d.toFixed(1))}K`;
}

export function minutesLabel(min) {
  if (!min) return null;
  const h = Math.floor(min / 60);
  const m = min % 60;
  if (!h) return `${m} min`;
  return m ? `${h} h ${m} min` : `${h} h`;
}

// "Under a week", "1 week", "6 weeks"
export function weeksLabel(n) {
  if (n < 1) return "Under a week";
  return n === 1 ? "1 week" : `${n} weeks`;
}

export function daysUntilLabel(days) {
  if (days === 0) return "Today";
  if (days === 1) return "Tomorrow";
  if (days < 0) return "Underway";
  if (days < 14) return `In ${days} days`;
  const w = Math.round(days / 7);
  if (days < 70) return `In ${w} weeks`;
  return `In ${Math.round(days / 30.4)} months`;
}

export const LEVEL_LABEL = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
  open: "Open",
};

export const REG_LABEL = {
  open: "Registration open",
  upcoming: "Opens soon",
  closed: "Registration closed",
  unknown: "Check organiser",
};

export const TERRAIN_LABEL = {
  road: "Road",
  trail: "Trail",
  track: "Track",
  "open-water": "Open water",
  pool: "Pool",
  velodrome: "Velodrome",
  court: "Court",
  turf: "Turf",
  indoor: "Indoor",
  mixed: "Mixed",
};

export function sportVar(slug) {
  return `var(--sport-${slug})`;
}

export function plural(n, word, many) {
  return `${n} ${n === 1 ? word : many || word + "s"}`;
}

// "sea swim, coastal tarmac" -> "Sea swim, coastal tarmac"
export function sentenceCase(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}
