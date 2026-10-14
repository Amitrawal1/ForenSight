import { useEffect, useState } from "react";
import { artifactUrl, deleteAnalysis, listAnalyses } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";
import { VERDICTS } from "../lib/verdicts.js";

const ICONS = { image: "🖼️", audio: "🎙️", video: "🎬" };

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

  if (error) return <p className="rounded-lg bg-rose-50 p-3 text-rose-700">{error}</p>;
  if (!items) return <p className="text-slate-500">Loading…</p>;

  return (
    <section>
      <h2 className="text-2xl font-bold">History</h2>
      <p className="mt-1 text-sm text-slate-500">Your past checks. Files stay on this server until you delete them.</p>

      {items.length === 0 ? (
        <div className="mt-6 rounded-xl border bg-white p-10 text-center text-slate-500">
          No checks yet.{" "}
          <button onClick={() => goTo("/")} className="text-blue-600 hover:underline">
            Check a file
          </button>
        </div>
      ) : (
        <ul className="mt-6 divide-y rounded-xl border bg-white">
          {items.map((a) => {
            const v = VERDICTS[a.verdict];
            return (
              <li
                key={a.id}
                onClick={() => goTo(`/analysis/${a.id}`)}
                className="flex cursor-pointer items-center gap-4 px-4 py-3 hover:bg-slate-50"
              >
                {/* Thumbnail for images and videos, an icon for audio */}
                <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100 text-2xl">
                  {a.thumbnail_path ? (
                    <img src={artifactUrl(a.id, a.thumbnail_path)} alt="" className="h-full w-full object-cover" />
                  ) : (
                    ICONS[a.media_type]
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{a.filename}</p>
                  <p className="text-xs text-slate-500">
                    {a.media_type} · {a.created_at ? new Date(a.created_at + "Z").toLocaleString() : ""}
                  </p>
                </div>
                {v ? (
                  <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${v.tone}`}>
                    {v.label}
                    {a.verdict !== "inconclusive" && a.confidence != null ? ` · ${Math.round(a.confidence * 100)}%` : ""}
                  </span>
                ) : (
                  <span className="shrink-0 text-xs text-slate-500">{a.status}</span>
                )}
                <button
                  onClick={(e) => remove(e, a)}
                  className="shrink-0 rounded px-2 py-1 text-xs text-slate-500 hover:bg-rose-50 hover:text-rose-700"
                  title="Delete this check"
                >
                  Delete
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
