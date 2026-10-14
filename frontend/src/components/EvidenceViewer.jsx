import { useState } from "react";
import { artifactUrl, originalUrl } from "../lib/api.js";

// Heatmaps that are drawn on top of the photo, with a short name and an explanation.
// (The frequency spectrum is a different kind of picture, so it gets its own panel.)
const OVERLAYS = {
  ai_image: { tab: "AI focus", help: "Red areas influenced the AI-image model most." },
  face_swap: { tab: "Faces", help: "Boxes show each face checked (red = suspicious). Red heat shows where the face model looked." },
  ela: { tab: "Edited areas", help: "Red areas recompress differently from the rest of the image, which can mean they were edited." },
};

// Pick the heatmap that best explains the verdict: the most trusted check that leans "fake",
// otherwise the faces view (if any), otherwise the first available.
function defaultTab(maps) {
  const leaning = maps.filter((d) => d.fake_score >= 0.5).sort((a, b) => b.reliability - a.reliability);
  if (leaning.length) return leaning[0].name;
  return (maps.find((d) => d.name === "face_swap") ?? maps[0])?.name ?? "original";
}

export default function EvidenceViewer({ id, detectors }) {
  const maps = detectors.filter((d) => d.heatmap && OVERLAYS[d.name]);
  const spectrum = detectors.find((d) => d.name === "fft" && d.heatmap);
  const [tab, setTab] = useState(() => defaultTab(maps));
  const [opacity, setOpacity] = useState(1);
  const active = maps.find((d) => d.name === tab);

  return (
    <section className="grid items-start gap-6 md:grid-cols-[2fr_1fr]">
      <div className="rounded-xl border bg-white p-4">
        {/* Tabs: original photo or one of the heatmaps */}
        <div className="mb-3 flex flex-wrap gap-2">
          {[{ name: "original" }, ...maps].map((d) => (
            <button
              key={d.name}
              onClick={() => setTab(d.name)}
              className={`rounded-full px-3 py-1 text-sm ${
                tab === d.name ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {d.name === "original" ? "Original" : OVERLAYS[d.name].tab}
            </button>
          ))}
        </div>

        <div className="relative">
          <img src={originalUrl(id)} alt="Uploaded file" className="w-full rounded" />
          {active && (
            // Heatmap images are the photo with colours added, so fading them shows the original below
            <img
              src={artifactUrl(id, active.heatmap)}
              alt={`${OVERLAYS[active.name].tab} heatmap`}
              className="absolute inset-0 h-full w-full rounded"
              style={{ opacity }}
            />
          )}
        </div>

        {active && (
          <>
            <p className="mt-3 text-sm text-slate-600">{OVERLAYS[active.name].help}</p>
            <label className="mt-2 flex items-center gap-3 text-sm text-slate-600">
              Heatmap strength
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={opacity}
                onChange={(e) => setOpacity(+e.target.value)}
                className="flex-1"
              />
            </label>
          </>
        )}
        {maps.length === 0 && <p className="mt-3 text-sm text-slate-500">No heatmaps for this file: no check found a suspicious area.</p>}
      </div>

      {spectrum && (
        <div className="rounded-xl border bg-white p-4">
          <h3 className="text-sm font-semibold">Frequency spectrum</h3>
          <img src={artifactUrl(id, spectrum.heatmap)} alt="Frequency spectrum" className="mt-2 w-full rounded" />
          <p className="mt-2 text-xs text-slate-500">
            A map of the image's fine, repeating patterns. Bright isolated dots away from the centre can be a trace of AI
            upsampling.
          </p>
        </div>
      )}
    </section>
  );
}
