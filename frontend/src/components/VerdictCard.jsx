import { reportUrl } from "../lib/api.js";
import { VERDICTS } from "../lib/verdicts.js";

// Timestamps from the backend are UTC, so we show them as UTC, like the PDF report does.
function formatDate(value) {
  if (!value) return null;
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return null;
  return `${date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })}, ${date.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  })} UTC`;
}

// Only the facts we really have, so older results simply show fewer of them.
function fileFacts(analysis) {
  const media = analysis.evidence?.media ?? {};
  const facts = [];
  if (analysis.media_type) facts.push(["Type", analysis.media_type[0].toUpperCase() + analysis.media_type.slice(1)]);
  if (media.duration_s) facts.push(["Duration", `${media.duration_s.toFixed(1)} s`]);
  if (media.width && media.height) facts.push(["Resolution", `${media.width} × ${media.height}`]);
  const date = formatDate(analysis.created_at);
  if (date) facts.push(["Date", date]);
  return facts;
}

// The top block of the result page: verdict, confidence, summary, file facts and buttons.
export default function VerdictCard({ analysis, onDelete }) {
  const v = VERDICTS[analysis.verdict] ?? VERDICTS.inconclusive;
  const color = v.color;
  const pct = Math.round((analysis.confidence ?? 0) * 100);
  const summary = analysis.evidence?.summary;
  const facts = fileFacts(analysis);

  return (
    <section className="overflow-hidden rounded-[32px] border border-navy bg-white">
      {/* Solid verdict block. Everything here is large, because small white text is hard to read on the amber colour. */}
      <div className="p-5 text-white sm:p-10" style={{ background: color }}>
        <p className="break-words text-xl font-bold">{analysis.filename}</p>
        <div className="mt-4 flex flex-wrap items-end justify-between gap-x-10 gap-y-4">
          <h1 className="min-w-0 text-[clamp(2.6rem,9vw,7.5rem)] font-extrabold leading-[0.95] tracking-tighter">{v.label}</h1>
          {analysis.verdict !== "inconclusive" && (
            <div className="shrink-0">
              <p className="text-[clamp(3rem,8vw,6.5rem)] font-extrabold leading-none tracking-tighter tabular-nums">{pct}%</p>
              <p className="mt-1 text-xl font-bold">Confidence</p>
            </div>
          )}
        </div>
        {summary && <p className="mt-6 max-w-3xl text-2xl font-semibold leading-snug tracking-tight sm:text-3xl">{summary}</p>}
      </div>

      {/* File facts and buttons on white */}
      <div className="flex flex-wrap items-center justify-between gap-x-10 gap-y-5 p-5 sm:px-10 sm:py-6">
        {facts.length > 0 && (
          <dl className="flex flex-wrap gap-x-10 gap-y-3">
            {facts.map(([name, value]) => (
              <div key={name}>
                <dt className="text-sm text-muted">{name}</dt>
                <dd className="text-lg font-semibold tracking-tight text-navy">{value}</dd>
              </div>
            ))}
          </dl>
        )}
        <div className="flex flex-wrap gap-3">
          <a href={reportUrl(analysis.id)} className="rounded-full bg-navy px-6 py-3 font-semibold text-white hover:bg-teal">
            Download PDF report
          </a>
          <button onClick={onDelete} className="rounded-full border border-navy px-6 py-3 font-semibold text-navy hover:bg-page">
            Delete
          </button>
        </div>
      </div>
    </section>
  );
}
