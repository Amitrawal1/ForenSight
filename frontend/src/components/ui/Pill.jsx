// Colours for each pill style. Text colours all pass the 4.5:1 contrast check.
const TONES = {
  teal: "bg-teal text-white",
  white: "bg-white text-navy",
  navy: "bg-navy text-white",
  outline: "border border-navy bg-transparent text-navy",
};

// A rounded label. Size comes from the className, so it works for small tags and giant headlines.
export default function Pill({ children, tone = "teal", className = "" }) {
  return <span className={`inline-flex items-center rounded-full px-[0.55em] py-[0.12em] ${TONES[tone] || TONES.teal} ${className}`}>{children}</span>;
}
