import { VERDICTS } from "../lib/verdicts.js";

export default function VerdictCard({ analysis }) {
  const v = VERDICTS[analysis.verdict] ?? VERDICTS.inconclusive;
  const pct = Math.round((analysis.confidence ?? 0) * 100);
  const { summary, reasons = [] } = analysis.evidence ?? {};

  return (
    <section className={`rounded-xl border p-6 ${v.tone}`}>
      <p className="text-sm opacity-80">{analysis.filename}</p>
      <h2 className="mt-1 text-3xl font-bold">{v.label}</h2>
      <p className="mt-2">{summary}</p>

      {analysis.verdict !== "inconclusive" && (
        <div className="mt-4">
          <div className="flex justify-between text-sm">
            <span>Confidence</span>
            <span className="font-semibold">{pct}%</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-white/70">
            <div className={`h-2 rounded-full ${v.bar}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {reasons.length > 0 && (
        <div className="mt-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide opacity-80">Why</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {reasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
