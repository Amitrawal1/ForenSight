// Per-check evidence: score, how much it is trusted, and its reasons.
export default function DetectorList({ detectors }) {
  if (!detectors.length) return null;
  return (
    <section className="rounded-xl border bg-white">
      <h3 className="border-b px-4 py-3 font-semibold">Evidence from each check</h3>
      <ul className="divide-y">
        {detectors.map((d) => (
          <li key={d.name} className="px-4 py-3">
            <details>
              <summary className="flex cursor-pointer items-center justify-between gap-4">
                <span className="font-medium">{d.label}</span>
                <span className="text-sm text-slate-500">
                  {d.reliability > 0 ? `fake score ${Math.round(d.fake_score * 100)}% · weight ${Math.round(d.reliability * 100)}%` : "info only"}
                </span>
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
    </section>
  );
}
