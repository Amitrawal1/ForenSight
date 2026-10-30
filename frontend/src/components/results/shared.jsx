import Pill from "../ui/Pill.jsx";

// Meaning colours. Used only for scores and verdicts, never for decoration.
export const REAL = "#1F7A5C";
export const UNSURE = "#B4690E";
export const FAKE = "#B4233C";

// Colour for a fake score: green (real), amber (unsure), red (fake)
export function scoreColor(score) {
  if (score >= 0.65) return FAKE;
  if (score <= 0.35) return REAL;
  return UNSURE;
}

export const pct = (value) => Math.round(value * 100);

// Seconds to "m:ss", for example 75 becomes "1:15"
export function mmss(s) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

// Big white card with a thin navy outline. Everything on the result page sits in one of these.
export function Card({ children, className = "" }) {
  return <div className={`rounded-[24px] border border-navy bg-white p-5 sm:p-8 ${className}`}>{children}</div>;
}

// Section headline: the first word in a solid pill, the rest as heavy plain text
export function Heading({ pill, tone = "teal", children }) {
  return (
    <h2 className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[clamp(1.7rem,3vw,2.6rem)] font-bold leading-[1.1] tracking-tight text-navy">
      <Pill tone={tone}>{pill}</Pill>
      {children && <span>{children}</span>}
    </h2>
  );
}
