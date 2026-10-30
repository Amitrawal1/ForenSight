import { useState } from "react";
import { artifactUrl, originalUrl } from "../lib/api.js";
import Lightbox from "./results/Lightbox.jsx";
import { Card, Heading, pct, scoreColor } from "./results/shared.jsx";

// Heatmaps are drawn on top of the photo, with a short name and an explanation.
const OVERLAYS = {
  ai_image: { title: "AI focus", help: "Red areas influenced the AI-image model most." },
  face_swap: { title: "Faces", help: "Boxes show each face checked (red = suspicious). Red heat shows where the face model looked." },
  ela: { title: "Edited areas", help: "Red areas recompress differently from the rest of the image, which can mean they were edited." },
};

// The frequency spectrum is not an overlay. It is a map of repeating patterns (made with an FFT, a maths
// tool that splits an image into patterns), not a picture of the photo, so its pixels do not line up with the photo.
const SPECTRUM_HELP =
  "A map of the image's fine, repeating patterns, not a picture of the photo. Bright isolated dots away from the centre can be a trace of AI upsampling.";

// Wide-screen columns for each number of pictures, so no card is left alone on a row.
// Five pictures use a 6-column grid: two wide cards on top, three below.
const COLUMNS = { 1: "lg:grid-cols-2", 2: "lg:grid-cols-2", 3: "lg:grid-cols-3", 4: "lg:grid-cols-4", 5: "lg:grid-cols-6" };

// One gallery card: picture, name, explanation and the check that made it. Click to enlarge.
function Tile({ item, onOpen, className }) {
  const d = item.detector;
  return (
    <Card className={`flex flex-col p-4! ${className}`}>
      <button onClick={onOpen} aria-label={`Enlarge ${item.title}`} className="block w-full cursor-zoom-in overflow-hidden rounded-[16px] bg-page">
        <img src={item.overlay ?? item.src} alt={item.overlay ? `${item.title} heatmap` : item.alt} className="aspect-[4/3] w-full object-contain" />
      </button>
      <h3 className="mt-4 text-2xl font-bold tracking-tight text-navy">{item.title}</h3>
      <p className="mt-1 flex-1 text-muted">{item.help}</p>
      {d && (
        <p className="mt-3 border-t border-line pt-3 text-sm text-navy">
          <span className="font-semibold">{d.label}</span>
          {d.reliability > 0 && (
            <>
              {" · "}
              <span className="font-bold" style={{ color: scoreColor(d.fake_score) }}>
                {pct(d.fake_score)}% fake
              </span>
              {` · trust ${pct(d.reliability)}%`}
            </>
          )}
        </p>
      )}
    </Card>
  );
}

// Image evidence: every picture we have, all visible at once, side by side.
export default function EvidenceViewer({ id, detectors = [] }) {
  const [open, setOpen] = useState(null);
  const src = originalUrl(id);

  const maps = Object.keys(OVERLAYS)
    .map((name) => detectors.find((d) => d.name === name && d.heatmap))
    .filter(Boolean);
  const spectrum = detectors.find((d) => d.name === "fft" && d.heatmap);

  const items = [
    { title: "Original", help: "The file as it was uploaded, with nothing added.", src, alt: "Uploaded file" },
    ...maps.map((d) => ({ ...OVERLAYS[d.name], src, alt: "Uploaded file", overlay: artifactUrl(id, d.heatmap), detector: d })),
    ...(spectrum ? [{ title: "Frequency spectrum", help: SPECTRUM_HELP, src: artifactUrl(id, spectrum.heatmap), alt: "Frequency spectrum", detector: spectrum }] : []),
  ];

  return (
    <section className="space-y-5">
      <Heading pill="Evidence">in the image</Heading>
      <div className={`grid gap-5 sm:grid-cols-2 ${COLUMNS[items.length]}`}>
        {items.map((item, i) => (
          <Tile
            key={item.title}
            item={item}
            onOpen={() => setOpen(item)}
            className={items.length === 5 ? (i < 2 ? "lg:col-span-3" : "lg:col-span-2") : ""}
          />
        ))}
      </div>
      {items.length === 1 && <p className="text-muted">No check produced a heatmap for this file.</p>}
      {open && <Lightbox item={open} onClose={() => setOpen(null)} />}
    </section>
  );
}
