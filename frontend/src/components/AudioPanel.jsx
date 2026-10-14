import { useRef, useState } from "react";
import { originalUrl } from "../lib/api.js";

// Audio player with the waveform drawn below it. Click the waveform to jump to that moment.
export default function AudioPanel({ id, media }) {
  const audio = useRef(null);
  const [time, setTime] = useState(0);
  const peaks = media?.peaks ?? [];
  const duration = media?.duration_s ?? 0;

  function seek(e) {
    if (!audio.current || !duration) return;
    const box = e.currentTarget.getBoundingClientRect();
    audio.current.currentTime = ((e.clientX - box.left) / box.width) * duration;
    audio.current.play();
  }

  return (
    <section className="rounded-xl border bg-white p-4">
      <audio ref={audio} src={originalUrl(id)} controls className="w-full" onTimeUpdate={(e) => setTime(e.target.currentTime)} />
      {peaks.length > 0 && (
        <svg
          viewBox={`0 0 ${peaks.length} 100`}
          preserveAspectRatio="none"
          className="mt-3 h-24 w-full cursor-pointer rounded bg-slate-50"
          onClick={seek}
        >
          {/* One thin bar per peak, mirrored around the middle line */}
          {peaks.map((p, i) => (
            <rect key={i} x={i} y={50 - p * 45} width={0.8} height={Math.max(1, p * 90)} className="fill-slate-400" />
          ))}
          {/* Red line = current playback position */}
          {duration > 0 && <rect x={(time / duration) * peaks.length} y={0} width={1.5} height={100} className="fill-rose-500" />}
        </svg>
      )}
      <p className="mt-1 text-xs text-slate-500">
        {duration.toFixed(1)} s · click the waveform to jump to that moment
      </p>
    </section>
  );
}
