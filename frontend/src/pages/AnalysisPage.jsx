import { useEffect, useState } from "react";
import { deleteAnalysis, getAnalysis, reportUrl } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";
import VerdictCard from "../components/VerdictCard.jsx";
import EvidenceViewer from "../components/EvidenceViewer.jsx";
import DetectorList from "../components/DetectorList.jsx";
import MediaPanel from "../components/MediaPanel.jsx";

const POLL_MS = 1500;

export default function AnalysisPage({ id }) {
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let timer;
    let cancelled = false;
    async function poll() {
      try {
        const a = await getAnalysis(id);
        if (cancelled) return;
        setAnalysis(a);
        if (a.status === "queued" || a.status === "processing") timer = setTimeout(poll, POLL_MS);
      } catch (e) {
        if (!cancelled) setError(e.message);
      }
    }
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [id]);

  const back = (
    <button onClick={() => goTo("/")} className="text-sm text-blue-600 hover:underline">
      ← Check another file
    </button>
  );

  if (error) return <div className="space-y-4">{back}<p className="text-rose-700">{error}</p></div>;
  if (!analysis || analysis.status === "queued" || analysis.status === "processing") {
    return (
      <div className="space-y-4">
        {back}
        <div className="rounded-xl border bg-white p-10 text-center">
          <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="mt-4 font-medium">Analysing {analysis?.filename ?? "file"}…</p>
          <p className="text-sm text-slate-500">{analysis?.status === "processing" ? "Running checks" : "Waiting in queue"}</p>
        </div>
      </div>
    );
  }
  if (analysis.status === "failed") {
    return (
      <div className="space-y-4">
        {back}
        <p className="rounded-lg bg-rose-50 p-4 text-rose-700">Analysis failed: {analysis.error}</p>
      </div>
    );
  }

  async function remove() {
    if (!window.confirm(`Delete "${analysis.filename}" and its results? This cannot be undone.`)) return;
    await deleteAnalysis(analysis.id);
    goTo("/history");
  }

  const ev = analysis.evidence ?? { detectors: [], reasons: [], notes: [] };
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        {back}
        <div className="flex gap-2">
          <a href={reportUrl(analysis.id)} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700">
            Download PDF report
          </a>
          <button onClick={remove} className="rounded-lg border px-4 py-2 text-sm text-slate-600 hover:bg-rose-50 hover:text-rose-700">
            Delete
          </button>
        </div>
      </div>
      <VerdictCard analysis={analysis} />
      {analysis.media_type === "image" && <EvidenceViewer id={analysis.id} detectors={ev.detectors} />}
      {(analysis.media_type === "audio" || analysis.media_type === "video") && (
        <MediaPanel id={analysis.id} kind={analysis.media_type} media={ev.media} detectors={ev.detectors} />
      )}
      {ev.notes?.length > 0 && (
        <ul className="space-y-1 text-sm text-slate-600">
          {ev.notes.map((n) => (
            <li key={n}>ℹ️ {n}</li>
          ))}
        </ul>
      )}
      <DetectorList detectors={ev.detectors} />
    </div>
  );
}
