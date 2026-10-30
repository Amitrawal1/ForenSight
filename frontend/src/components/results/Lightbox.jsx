import { useEffect, useRef, useState } from "react";

// Enlarged view of one evidence picture.
// When "overlay" is given, the slider fades it to show the original underneath.
export default function Lightbox({ item, onClose }) {
  const dialog = useRef(null);
  const [opacity, setOpacity] = useState(1);

  // showModal gives us the dark backdrop, the Esc key and keyboard focus for free
  useEffect(() => {
    dialog.current.showModal();
  }, []);

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      // A click on the backdrop lands on the dialog itself, so close in that case
      onClick={(e) => e.target === dialog.current && dialog.current.close()}
      className="m-auto max-h-[94vh] w-fit max-w-[min(94vw,1280px)] rounded-[24px] border border-navy bg-white p-4 text-navy backdrop:bg-navy/80 sm:p-6"
    >
      <div className="mb-3 flex items-start justify-between gap-4">
        <h3 className="text-2xl font-bold tracking-tight">{item.title}</h3>
        <button onClick={() => dialog.current.close()} className="shrink-0 rounded-full bg-navy px-4 py-1.5 font-semibold text-white">
          Close
        </button>
      </div>

      <div className="relative mx-auto w-fit">
        <img src={item.src} alt={item.alt} className="max-h-[68vh] w-auto max-w-full rounded-[16px]" />
        {item.overlay && (
          // Heatmap images are the photo with colours added, so fading them shows the original below
          <img src={item.overlay} alt={`${item.title} heatmap`} className="absolute inset-0 h-full w-full rounded-[16px]" style={{ opacity }} />
        )}
      </div>

      <p className="mt-3 max-w-2xl text-muted">{item.help}</p>
      {item.overlay && (
        <label className="mt-2 flex items-center gap-3 font-semibold">
          Heatmap strength
          <input type="range" min="0" max="1" step="0.05" value={opacity} onChange={(e) => setOpacity(+e.target.value)} className="flex-1 accent-teal" />
        </label>
      )}
    </dialog>
  );
}
