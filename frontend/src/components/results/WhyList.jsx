import { Card, Heading } from "./shared.jsx";

// The plain-English reasons behind the verdict, as a numbered list of large statements.
export default function WhyList({ reasons = [] }) {
  if (!reasons.length) return null;
  return (
    <section className="space-y-5">
      <Heading pill="Why">we say this</Heading>
      <Card>
        <ol className="divide-y divide-line">
          {reasons.map((r, i) => (
            <li key={i} className="flex gap-4 py-5 first:pt-0 last:pb-0 sm:gap-8">
              <span className="w-10 shrink-0 text-4xl font-bold leading-none tracking-tight text-teal tabular-nums sm:w-14 sm:text-5xl">{i + 1}</span>
              <p className="text-xl font-medium leading-snug tracking-tight text-navy sm:text-2xl">{r}</p>
            </li>
          ))}
        </ol>
      </Card>
    </section>
  );
}
