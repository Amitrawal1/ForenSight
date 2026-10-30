import { Card, Heading, pct, scoreColor } from "./results/shared.jsx";

const KIND_NAMES = { ai_generated: "AI-generated", manipulated: "Manipulated" };

// One check, always open: name, fake score, trust, bar and every reason it gave.
function CheckCard({ d }) {
  const scored = d.reliability > 0;
  const color = scoreColor(d.fake_score);
  return (
    <Card className="flex flex-col lg:odd:last:col-span-2">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-2xl font-bold leading-tight tracking-tight text-navy">{d.label}</h3>
          <p className="mt-1 text-sm text-muted">{scored ? `Looks for: ${KIND_NAMES[d.fake_kind] ?? d.fake_kind}` : "Info only, not counted in the verdict"}</p>
        </div>
        {scored && (
          <div className="shrink-0 text-right">
            <p className="text-5xl font-extrabold leading-none tracking-tighter tabular-nums" style={{ color }}>
              {pct(d.fake_score)}%
            </p>
            <p className="mt-1 text-sm font-semibold text-navy">fake · trust {pct(d.reliability)}%</p>
          </div>
        )}
      </div>

      {scored && (
        // Fake-score bar: green = looks real, red = looks fake
        <div className="mt-4 h-3 rounded-full bg-page">
          <div className="h-full rounded-full" style={{ width: `${Math.max(2, d.fake_score * 100)}%`, background: color }} />
        </div>
      )}

      {d.reasons?.length > 0 && (
        <ul className="mt-4 space-y-2 text-navy">
          {d.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

// Per-check evidence, plus notes such as checks that were skipped.
export default function DetectorList({ detectors = [], notes = [] }) {
  if (!detectors.length && !notes.length) return null;
  // Most trusted checks first
  const sorted = [...detectors].sort((a, b) => b.reliability - a.reliability);

  return (
    <section className="space-y-5">
      <Heading pill="Checks">that ran</Heading>
      {sorted.length > 0 && (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            {sorted.map((d) => (
              <CheckCard key={d.name} d={d} />
            ))}
          </div>
          <p className="text-muted">"Trust" is how much each check counts in the final verdict. Learned models count more than simple checks.</p>
        </>
      )}
      {notes.length > 0 && (
        <div className="space-y-1 text-navy">
          {notes.map((n, i) => (
            <p key={i}>{n}</p>
          ))}
        </div>
      )}
    </section>
  );
}
