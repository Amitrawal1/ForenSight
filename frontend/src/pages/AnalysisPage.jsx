import { useEffect, useState } from "react";
import { deleteAnalysis, getAnalysis } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";
import VerdictCard from "../components/VerdictCard.jsx";
import EvidenceViewer from "../components/EvidenceViewer.jsx";
import DetectorList from "../components/DetectorList.jsx";
import MediaPanel from "../components/MediaPanel.jsx";
import WhyList from "../components/results/WhyList.jsx";
import HowReached from "../components/results/HowReached.jsx";
import { Card } from "../components/results/shared.jsx";
import Pill from "../components/ui/Pill.jsx";
import ProgressBar from "../components/ui/ProgressBar.jsx";

const POLL_MS = 1000;

// Shown while the file waits for its turn or is being checked.
function Waiting({ analysis }) {
  const queued = !analysis || analysis.status === "queued";
  const percent = analysis?.progress?.percent;
  const known = !queued && percent != null;
  const label = queued ? "Waiting in queue" : analysis.progress?.step ?? "Running checks";
  return (
    <Card className="sm:p-12!">
      <p className="break-words text-[clamp(1.7rem,3vw,2.6rem)] font-bold leading-[1.1] tracking-tight text-navy">
        <Pill tone="teal">Analysing</Pill> {analysis?.filename ?? "file"}
      </p>
      <div className="mt-8">
        {/* No progress number yet: show the moving bar instead of making one up */}
        <ProgressBar percent={known ? percent : 0} label={label} indeterminate={!known} />
      </div>
    </Card>
  );
}

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
    <button onClick={() => goTo("/")} className="font-semibold text-teal hover:underline">
      ← Check another file
    </button>
  );

  if (error) {
    return (
      <div className="space-y-5">
        {back}
        <Card>
          <p className="text-xl font-medium text-navy">{error}</p>
        </Card>
      </div>
    );
  }
  if (!analysis || analysis.status === "queued" || analysis.status === "processing") {
    return (
      <div className="space-y-5">
        {back}
        <Waiting analysis={analysis} />
      </div>
    );
  }
  if (analysis.status === "failed") {
    return (
      <div className="space-y-5">
        {back}
        <Card className="sm:p-12!">
          <p className="break-words text-[clamp(1.7rem,3vw,2.6rem)] font-bold leading-[1.1] tracking-tight text-navy">
            <Pill tone="navy">Analysis failed</Pill> {analysis.filename}
          </p>
          <p className="mt-6 break-words text-xl font-medium text-navy">{analysis.error ?? "The server did not give a reason."}</p>
          <button onClick={() => goTo("/")} className="mt-6 rounded-full bg-teal px-6 py-3 font-semibold text-white">
            Please try again
          </button>
        </Card>
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
    <div className="space-y-10 sm:space-y-14">
      <div className="space-y-5">
        {back}
        <VerdictCard analysis={analysis} onDelete={remove} />
      </div>
      <WhyList reasons={ev.reasons} />
      <HowReached detectors={ev.detectors} />
      {analysis.media_type === "image" && <EvidenceViewer id={analysis.id} detectors={ev.detectors} />}
      {(analysis.media_type === "audio" || analysis.media_type === "video") && (
        <MediaPanel id={analysis.id} kind={analysis.media_type} media={ev.media} detectors={ev.detectors} />
      )}
      <DetectorList detectors={ev.detectors} notes={ev.notes} />
      <div className="rounded-[24px] bg-navy p-6 text-white sm:p-10">
        <p className="text-2xl font-bold leading-snug tracking-tight sm:text-3xl">This verdict supports human judgement. It is not final proof.</p>
        <p className="mt-2 text-lg">Automated checks can be wrong. Consider where the file came from and its context before acting on it.</p>
      </div>
    </div>
  );
}
