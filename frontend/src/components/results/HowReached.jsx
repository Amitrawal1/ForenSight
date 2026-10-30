import { Card, Heading, pct, scoreColor } from "./shared.jsx";

// The two cut-off lines from backend/app/pipeline/fusion/combiner.py (AUTHENTIC_BELOW and FAKE_ABOVE).
const AUTHENTIC_BELOW = 0.35;
const FAKE_ABOVE = 0.65;

const GROUPS = [
  { kind: "ai_generated", title: "AI-generated", help: "Was the whole file made by AI?" },
  { kind: "manipulated", title: "Manipulated", help: "Was a real file changed or edited?" },
];

// Columns shared by the axis and every row, so the bars and cut-off lines all line up.
const ROW = "grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1 md:grid-cols-[210px_1fr_64px_130px]";

// Dashed cut-off lines drawn on top of a score bar
function CutOffLines() {
  return [AUTHENTIC_BELOW, FAKE_ABOVE].map((at) => (
    <div key={at} className="pointer-events-none absolute -bottom-1.5 -top-1.5 border-l-2 border-dashed border-navy" style={{ left: `${at * 100}%` }} />
  ));
}

// Number scale above the bars
function Axis() {
  const ticks = [0, AUTHENTIC_BELOW, FAKE_ABOVE, 1];
  return (
    <div className={`${ROW} mb-2 text-xs font-semibold text-muted`}>
      <div className="relative col-span-2 h-4 md:col-span-1 md:col-start-2">
        {ticks.map((t) => (
          <span key={t} className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full" style={{ left: `${t * 100}%` }}>
            {pct(t)}%
          </span>
        ))}
      </div>
    </div>
  );
}

// One check: name, fake score on the shared scale, and how much it is trusted
function Row({ d }) {
  const title = `${d.label}: ${pct(d.fake_score)}% fake, trust ${pct(d.reliability)}%`;
  return (
    <li className={ROW} title={title}>
      <span className="font-semibold leading-tight text-navy md:order-1">{d.label}</span>
      <span className="text-right text-2xl font-bold tracking-tight tabular-nums md:order-3" style={{ color: scoreColor(d.fake_score) }}>
        {pct(d.fake_score)}%
      </span>
      <div className="relative col-span-2 h-5 rounded-full bg-page md:order-2 md:col-span-1">
        <div className="h-full rounded-full" style={{ width: `${Math.max(2, d.fake_score * 100)}%`, background: scoreColor(d.fake_score) }} />
        <CutOffLines />
      </div>
      {/* Trust has its own small bar, so it is not mistaken for part of the fake score */}
      <div className="col-span-2 flex items-center gap-2 text-sm text-muted md:order-4 md:col-span-1">
        <span className="whitespace-nowrap tabular-nums">Trust {pct(d.reliability)}%</span>
        <div className="h-2 flex-1 rounded-full bg-page">
          <div className="h-full rounded-full bg-teal" style={{ width: `${d.reliability * 100}%` }} />
        </div>
      </div>
    </li>
  );
}

// An honest picture of what went into the verdict. It only draws values the backend sent.
// It does not work out a combined score here, because that is the backend's job.
export default function HowReached({ detectors = [] }) {
  const scored = detectors.filter((d) => d.reliability > 0);
  const infoOnly = detectors.filter((d) => !(d.reliability > 0));
  if (!detectors.length) return null;

  // Same rule as the combiner: the strongest proof-like finding decides on its own
  const proofs = detectors.filter((d) => d.decisive && d.fake_score > FAKE_ABOVE);
  const proof = proofs.length ? proofs.reduce((a, b) => (b.fake_score > a.fake_score ? b : a)) : null;

  return (
    <section className="space-y-5">
      <Heading pill="How">the verdict was reached</Heading>
      <Card className="space-y-8">
        {proof && (
          <div className="rounded-[16px] bg-navy p-5 text-white sm:p-6">
            <p className="text-xl font-bold tracking-tight sm:text-2xl">{proof.label} decided this verdict.</p>
            <p className="mt-2 text-white/90">
              It found proof-like information, which decides on its own. {proof.reasons?.[0]} The scores below did not change the result.
            </p>
          </div>
        )}

        {GROUPS.map((g) => {
          const rows = scored.filter((d) => d.fake_kind === g.kind).sort((a, b) => b.reliability - a.reliability);
          if (!rows.length) return null;
          return (
            <div key={g.kind}>
              <h3 className="text-2xl font-bold tracking-tight text-navy">{g.title}</h3>
              <p className="mb-4 text-muted">{g.help}</p>
              <Axis />
              <ul className="space-y-4">
                {rows.map((d) => (
                  <Row key={d.name} d={d} />
                ))}
              </ul>
            </div>
          );
        })}

        {infoOnly.length > 0 && (
          <div>
            <h3 className="text-2xl font-bold tracking-tight text-navy">Info only</h3>
            <p className="text-muted">
              {infoOnly.map((d) => d.label).join(", ")}: shown for information and not counted in the verdict.
            </p>
          </div>
        )}

        <div className="space-y-2 border-t border-line pt-5 text-muted">
          <p>
            <span className="font-semibold text-navy">The dashed lines mark 35% and 65%.</span> The final score is judged against them, not each check on its own.
          </p>
          <p>
            That score combines the checks of each kind, weighted by trust, and includes a neutral 50% starting guess so that one weak check cannot decide
            alone. So it is not a simple average of these bars. Above 65% gives a fake verdict. "Likely Authentic" needs enough evidence, scores below 35%, and
            no check strongly suspecting a fake. Anything else is "Inconclusive".
          </p>
        </div>
      </Card>
    </section>
  );
}
