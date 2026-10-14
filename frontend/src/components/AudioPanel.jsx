import { useRef, useState } from "react";
import { originalUrl } from "../lib/api.js";

// Colour for a fake score: green (real) -> amber (unsure) -> red (fake)
function scoreColor(score) {
  if (score >= 0.65) return "#f43f5e";
  if (score >= 0.5) return "#fb923c";
  if (score > 0.35) return "#facc15";
  return "#34d399";
}

function mmss(s) {
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

// Audio player + waveform + one timeline row per audio check.
// Click anywhere on the waveform or a timeline row to jump to that moment.
export default function AudioPanel({ id, media, detectors = [] }) {
  const audio = useRef(null);
  const [time, setTime] = useState(0);
  const peaks = media?.peaks ?? [];
  const duration = media?.duration_s ?? 0;
  const rows = detectors.filter((d) => d.segments?.length > 0);

  function seekTo(seconds) {
    if (!audio.current) return;
    audio.current.currentTime = seconds;
    audio.current.play();
  }

  function seekFromClick(e) {
    if (!duration) return;
    const box = e.currentTarget.getBoundingClientRect();
    seekTo(((e.clientX - box.left) / box.width) * duration);
  }

  // Red playhead line, shared by the waveform and every timeline row
  const playhead = duration > 0 && (
    <div className="pointer-events-none absolute top-0 h-full w-0.5 bg-rose-600" style={{ left: `${(time / duration) * 100}%` }} />
  );

  return (
    <section className="rounded-xl border bg-white p-4">
      <audio ref={audio} src={originalUrl(id)} controls className="w-full" onTimeUpdate={(e) => setTime(e.target.currentTime)} />

      {peaks.length > 0 && (
        <div className="relative mt-3 cursor-pointer" onClick={seekFromClick}>
          <svg viewBox={`0 0 ${peaks.length} 100`} preserveAspectRatio="none" className="h-24 w-full rounded bg-slate-50">
            {/* One thin bar per peak, mirrored around the middle line */}
            {peaks.map((p, i) => (
              <rect key={i} x={i} y={50 - p * 45} width={0.8} height={Math.max(1, p * 90)} className="fill-slate-400" />
            ))}
          </svg>
          {playhead}
        </div>
      )}

      {/* Timeline: one row per check that scored parts of the audio */}
      {duration > 0 &&
        rows.map((d) => (
          <div key={d.name} className="mt-2">
            <p className="text-xs font-medium text-slate-600">{d.label}</p>
            <div className="relative mt-1 h-5 cursor-pointer rounded bg-slate-100" onClick={seekFromClick}>
              {d.segments.map((s, i) => (
                <div
                  key={i}
                  title={`${mmss(s.start_s)}-${mmss(s.end_s)}: ${Math.round(s.score * 100)}% fake`}
                  className="absolute top-0 h-full rounded-sm opacity-80"
                  style={{
                    left: `${(s.start_s / duration) * 100}%`,
                    width: `${(Math.min(s.end_s, duration) - s.start_s) / duration * 100}%`,
                    background: scoreColor(s.score),
                  }}
                />
              ))}
              {playhead}
            </div>
          </div>
        ))}

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>{duration.toFixed(1)} s · click anywhere to jump to that moment</span>
        {rows.length > 0 && (
          <span className="flex items-center gap-3">
            <span><span className="mr-1 inline-block h-2 w-3 rounded-sm" style={{ background: "#34d399" }} />real</span>
            <span><span className="mr-1 inline-block h-2 w-3 rounded-sm" style={{ background: "#facc15" }} />unsure</span>
            <span><span className="mr-1 inline-block h-2 w-3 rounded-sm" style={{ background: "#f43f5e" }} />fake</span>
          </span>
        )}
      </div>
    </section>
  );
}
