// Per-check evidence: how "fake" each check thinks the file is, how much we trust it, and its reasons.

function barColor(score) {
  if (score >= 0.65) return "bg-rose-500";
  if (score <= 0.35) return "bg-emerald-500";
  return "bg-amber-400";
}

export default function DetectorList({ detectors }) {
  if (!detectors.length) return null;
  // Most trusted checks first
  const sorted = [...detectors].sort((a, b) => b.reliability - a.reliability);

  return (
    <section className="rounded-xl border bg-white">
      <h3 className="border-b px-4 py-3 font-semibold">Evidence from each check</h3>
      <ul className="divide-y">
        {sorted.map((d) => (
          <li key={d.name} className="px-4 py-3">
            <details>
              <summary className="flex cursor-pointer items-center gap-4">
                <span className="w-40 shrink-0 font-medium">{d.label}</span>
                {d.reliability > 0 ? (
                  <>
                    {/* Fake-score bar: green = looks real, red = looks fake */}
                    <div className="h-2 flex-1 rounded-full bg-slate-100">
                      <div className={`h-2 rounded-full ${barColor(d.fake_score)}`} style={{ width: `${Math.max(2, d.fake_score * 100)}%` }} />
                    </div>
                    <span className="w-44 shrink-0 text-right text-xs text-slate-500">
                      {Math.round(d.fake_score * 100)}% fake · trust {Math.round(d.reliability * 100)}%
                    </span>
                  </>
                ) : (
                  <span className="flex-1 text-right text-xs text-slate-500">info only</span>
                )}
              </summary>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
                {d.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </details>
          </li>
        ))}
      </ul>
      <p className="border-t px-4 py-2 text-xs text-slate-500">
        "Trust" is how much each check counts in the final verdict. Learned models count more than simple checks.
      </p>
    </section>
  );
}
