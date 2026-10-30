import { useEffect, useState } from "react";
import Pill from "../components/ui/Pill.jsx";
import { artifactUrl, deleteAnalysis, listAnalyses } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";
import { VERDICTS } from "../lib/verdicts.js";

// Simple line drawings shown when a check has no thumbnail.
const ICONS = {
  image: <path d="M4 6h16v12H4zM4 16l5-5 4 4 2-2 5 5" />,
  audio: <path d="M5 10v4M9 7v10M13 4v16M17 8v8M21 11v2" />,
  video: <path d="M4 6h11v12H4zM15 11l6-4v10l-6-4" />,
};

function MediaIcon({ type }) {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[type]}
    </svg>
  );
}

// Same page width and spacing for every state of this page (loading, error, list).
function Shell({ children }) {
  return <section className="mx-auto w-full max-w-6xl px-4 pt-8 pb-20 sm:px-8 sm:pt-14">{children}</section>;
}

// List of all past checks: thumbnail, file name, verdict, date. Click to open, or delete.
export default function HistoryPage() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    listAnalyses().then(setItems).catch((e) => setError(e.message));
  }, []);

  async function remove(e, item) {
    e.stopPropagation(); // don't also open the result page
    if (!window.confirm(`Delete "${item.filename}" and its results? This cannot be undone.`)) return;
    try {
      await deleteAnalysis(item.id);
      setItems((list) => list.filter((a) => a.id !== item.id));
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) {
    return (
      <Shell>
        <p role="alert" className="rounded-3xl border border-navy bg-white px-6 py-4 font-medium">
          {error}
        </p>
      </Shell>
    );
  }
  if (!items) {
    return (
      <Shell>
        <p className="text-lg text-muted">Loading…</p>
      </Shell>
    );
  }

  return (
    <Shell>
      <h2 className="flex items-center gap-[0.14em] text-5xl leading-tight font-semibold tracking-tight sm:text-6xl">
        <Pill tone="teal">History</Pill>
        <span className="block h-[1.39em] w-[1.39em] shrink-0 rounded-full bg-white" aria-hidden="true" />
      </h2>
      <p className="mt-6 text-xl leading-snug text-muted">Your past checks. Files stay on this server until you delete them.</p>

      {items.length === 0 ? (
        <div className="mt-10 rounded-card border border-navy bg-white p-10 text-center text-lg">
          <p className="text-muted">No checks yet.</p>
          <button onClick={() => goTo("/")} className="lift mt-5 rounded-full bg-teal px-6 py-2.5 text-lg font-semibold tracking-tight text-white">
            Check a file
          </button>
        </div>
      ) : (
        <ul className="mt-10 space-y-3">
          {items.map((a) => {
            const v = VERDICTS[a.verdict];
            return (
              <li
                key={a.id}
                onClick={() => goTo(`/analysis/${a.id}`)}
                className="flex cursor-pointer flex-wrap items-center gap-x-4 gap-y-3 rounded-card border border-navy bg-white p-3 pr-5 transition-colors hover:border-teal sm:flex-nowrap sm:gap-5"
              >
                {/* Thumbnail for images and videos, an icon for audio */}
                <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-[16px] border border-line bg-page sm:h-20 sm:w-20">
                  {a.thumbnail_path ? <img src={artifactUrl(a.id, a.thumbnail_path)} alt="" className="h-full w-full object-cover" /> : <MediaIcon type={a.media_type} />}
                </div>
                <div className="min-w-0 flex-1 basis-40">
                  {/* A real button lets keyboard users open the row. Its click reaches the row's handler above. */}
                  <button className="block max-w-full truncate rounded text-left text-lg font-semibold tracking-tight sm:text-xl">{a.filename}</button>
                  <p className="mt-0.5 text-sm text-muted">
                    {a.media_type} · {a.created_at ? new Date(a.created_at + "Z").toLocaleString() : ""}
                  </p>
                </div>
                {v ? (
                  <span className={`shrink-0 rounded-full border px-3.5 py-1.5 text-sm font-semibold ${v.tone}`}>
                    {v.label}
                    {a.verdict !== "inconclusive" && a.confidence != null ? ` · ${Math.round(a.confidence * 100)}%` : ""}
                  </span>
                ) : (
                  <span className="shrink-0 text-sm text-muted">{a.status}</span>
                )}
                <button onClick={(e) => remove(e, a)} className="lift ml-auto shrink-0 rounded-full border border-navy px-4 py-1.5 text-sm font-semibold hover:bg-navy hover:text-white sm:ml-0" title="Delete this check">
                  Delete
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </Shell>
  );
}
