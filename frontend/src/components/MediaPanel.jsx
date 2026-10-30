import { useRef, useState } from "react";
import { artifactUrl, originalUrl } from "../lib/api.js";
import { Card, FAKE, Heading, mmss, pct, REAL, scoreColor, UNSURE } from "./results/shared.jsx";

// The two video checks shown under each frame in the frame strip
const FRAME_CHECKS = [
  { name: "video_face_swap", short: "Face swap" },
  { name: "video_ai_frames", short: "AI frame" },
];

// Find the part of a check that covers this moment. A moment at the very end still counts for the last part.
function segmentAt(segments = [], time) {
  return segments.find((s) => time >= s.start_s && time < s.end_s) ?? segments.find((s) => time === s.end_s);
}

// Audio or video evidence: player, waveform, one timeline row per check, and any pictures we have.
// Click the waveform, a timeline row or a frame to jump to that moment.
export default function MediaPanel({ id, kind, media, detectors = [] }) {
  const player = useRef(null); // the <audio> or <video> element
  const [time, setTime] = useState(0);
  const peaks = media?.peaks ?? [];
  const duration = media?.duration_s ?? 0;
  const thumbs = media?.frames ?? [];
  const rows = detectors.filter((d) => d.segments?.length > 0);

  function seekTo(seconds) {
    if (!player.current) return;
    player.current.currentTime = seconds;
    player.current.play()?.catch(() => {}); // The browser may refuse to autoplay; the jump still works
  }

  function seekFromClick(e) {
    if (!duration) return;
    const box = e.currentTarget.getBoundingClientRect();
    seekTo(((e.clientX - box.left) / box.width) * duration);
  }

  // Playhead line, shared by the waveform and every timeline row
  const playhead = duration > 0 && (
    <div className="pointer-events-none absolute top-0 h-full w-0.5 bg-navy" style={{ left: `${(time / duration) * 100}%` }} />
  );

  // Video checks that saved a picture of their most suspicious frame
  const worstFrames = detectors.filter((d) => kind === "video" && d.heatmap && d.segments?.length > 0);
  const hasTimeline = peaks.length > 0 || (duration > 0 && rows.length > 0);

  return (
    <section className="space-y-5">
      <Heading pill="Evidence">{kind === "video" ? "in the video" : "in the audio"}</Heading>

      <div className={`grid items-start gap-5 ${worstFrames.length ? "lg:grid-cols-2" : ""}`}>
        <Card>
          {kind === "video" ? (
            <video ref={player} src={originalUrl(id)} controls className="max-h-[480px] w-full rounded-[20px] bg-navy" onTimeUpdate={(e) => setTime(e.target.currentTime)} />
          ) : (
            <audio ref={player} src={originalUrl(id)} controls className="w-full" onTimeUpdate={(e) => setTime(e.target.currentTime)} />
          )}
        </Card>

        {/* Most suspicious frame, with the face-swap heatmap and a button to jump there */}
        {worstFrames.map((d) => {
          const worst = d.segments.reduce((a, b) => (b.score > a.score ? b : a));
          const at = (worst.start_s + worst.end_s) / 2;
          return (
            <Card key={d.name}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-2xl font-bold tracking-tight text-navy">Most suspicious frame ({mmss(at)})</h3>
                <button onClick={() => seekTo(at)} className="rounded-full bg-teal px-4 py-1.5 font-semibold text-white">
                  Jump to {mmss(at)}
                </button>
              </div>
              <img src={artifactUrl(id, d.heatmap)} alt="Most suspicious frame" className="mt-4 max-h-[480px] w-full rounded-[20px] bg-page object-contain" />
              <p className="mt-3 text-muted">Boxes show each face checked (red = suspicious). Red heat shows where the face model looked.</p>
              <p className="mt-2 text-sm text-navy">
                <span className="font-semibold">{d.label}</span>
                {" · this part "}
                <span className="font-bold" style={{ color: scoreColor(worst.score) }}>
                  {pct(worst.score)}% fake
                </span>
              </p>
            </Card>
          );
        })}
      </div>

      {hasTimeline && (
        <Card>
          <h3 className="text-2xl font-bold tracking-tight text-navy">Timeline</h3>

          {peaks.length > 0 && (
            <div className="relative mt-4 cursor-pointer" onClick={seekFromClick}>
              <svg viewBox={`0 0 ${peaks.length} 100`} preserveAspectRatio="none" className="h-24 w-full rounded-[12px] bg-page">
                {/* One thin bar per peak, mirrored around the middle line */}
                {peaks.map((p, i) => (
                  <rect key={i} x={i} y={50 - p * 45} width={0.8} height={Math.max(1, p * 90)} className="fill-teal" />
                ))}
              </svg>
              {playhead}
            </div>
          )}

          {/* One row per check that scored parts of the file */}
          {duration > 0 &&
            rows.map((d) => (
              <div key={d.name} className="mt-4">
                <p className="text-sm font-semibold text-navy">{d.label}</p>
                <div className="relative h-5 cursor-pointer mt-1 overflow-hidden rounded-full bg-page" onClick={seekFromClick}>
                  {d.segments.map((s, i) => (
                    <div
                      key={i}
                      title={`${mmss(s.start_s)}-${mmss(s.end_s)}: ${pct(s.score)}% fake`}
                      className="absolute top-0 h-full"
                      style={{
                        left: `${(s.start_s / duration) * 100}%`,
                        width: `${((Math.min(s.end_s, duration) - s.start_s) / duration) * 100}%`,
                        background: scoreColor(s.score),
                      }}
                    />
                  ))}
                  {playhead}
                </div>
              </div>
            ))}

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
            <span>{duration > 0 && `${duration.toFixed(1)} s · `}click anywhere to jump to that moment</span>
            {rows.length > 0 && (
              <span className="flex items-center gap-3">
                {[["real", REAL], ["unsure", UNSURE], ["fake", FAKE]].map(([name, color]) => (
                  <span key={name}>
                    <span className="mr-1 inline-block h-2 w-3 rounded-sm" style={{ background: color }} />
                    {name}
                  </span>
                ))}
              </span>
            )}
          </div>
        </Card>
      )}

      {/* Every sampled frame, with what each video check said about that moment */}
      {thumbs.length > 0 && (
        <Card>
          <h3 className="text-2xl font-bold tracking-tight text-navy">Frame by frame</h3>
          <p className="mt-1 text-muted">Each sampled frame with its score from the video checks. Click a frame to jump there.</p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {thumbs.map((f) => (
              <button key={f.file} onClick={() => seekTo(f.time_s)} className="min-w-0 text-left">
                <img src={artifactUrl(id, f.file)} alt={`Frame at ${mmss(f.time_s)}`} className="aspect-video w-full rounded-[12px] bg-navy object-contain" />
                <p className="mt-1 text-sm font-bold text-navy tabular-nums">{mmss(f.time_s)}</p>
                {FRAME_CHECKS.map((c) => {
                  const seg = segmentAt(detectors.find((d) => d.name === c.name)?.segments, f.time_s);
                  if (!seg) return null;
                  return (
                    <div key={c.name} className="mt-1">
                      <p className="flex justify-between text-xs text-muted">
                        <span>{c.short}</span>
                        <span className="font-semibold tabular-nums">{pct(seg.score)}%</span>
                      </p>
                      <div className="h-1.5 rounded-full bg-page">
                        <div className="h-full rounded-full" style={{ width: `${Math.max(3, seg.score * 100)}%`, background: scoreColor(seg.score) }} />
                      </div>
                    </div>
                  );
                })}
              </button>
            ))}
          </div>
        </Card>
      )}

      {media?.spectrogram && (
        <Card>
          <h3 className="text-2xl font-bold tracking-tight text-navy">Spectrogram</h3>
          <p className="mt-1 text-muted">A picture of the sound: time runs left to right, pitch runs bottom to top, and brighter means louder.</p>
          <img src={artifactUrl(id, media.spectrogram)} alt="Spectrogram" className="mt-4 w-full rounded-[20px]" />
        </Card>
      )}
    </section>
  );
}
