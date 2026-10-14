import { useState } from "react";
import { artifactUrl, originalUrl } from "../lib/api.js";

// Original image with an optional heatmap overlay (opacity slider).
export default function EvidenceViewer({ id, detectors }) {
  const ela = detectors.find((d) => d.name === "ela" && d.heatmap);
  const fft = detectors.find((d) => d.name === "fft" && d.heatmap);
  const [opacity, setOpacity] = useState(ela ? 0.7 : 0);

  return (
    <section className="grid gap-6 md:grid-cols-[2fr_1fr]">
      <div className="rounded-xl border bg-white p-4">
        <div className="relative">
          <img src={originalUrl(id)} alt="Uploaded file" className="w-full rounded" />
          {ela && (
            <img
              src={artifactUrl(id, ela.heatmap)}
              alt="Error level heatmap"
              className="absolute inset-0 h-full w-full rounded"
              style={{ opacity }}
            />
          )}
        </div>
        {ela && (
          <label className="mt-3 flex items-center gap-3 text-sm text-slate-600">
            Heatmap
            <input type="range" min="0" max="1" step="0.05" value={opacity} onChange={(e) => setOpacity(+e.target.value)} className="flex-1" />
          </label>
        )}
      </div>
      {fft && (
        <div className="rounded-xl border bg-white p-4">
          <h3 className="text-sm font-semibold">Frequency spectrum</h3>
          <img src={artifactUrl(id, fft.heatmap)} alt="Frequency spectrum" className="mt-2 w-full rounded" />
          <p className="mt-2 text-xs text-slate-500">Bright isolated dots away from the centre can indicate AI upsampling patterns.</p>
        </div>
      )}
    </section>
  );
}
