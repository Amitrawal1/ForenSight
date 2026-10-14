import { useRef, useState } from "react";
import { uploadFile } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.wav,.mp3,.m4a,.ogg,.opus";

export default function UploadPage() {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function send(file) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const analysis = await uploadFile(file);
      goTo(`/analysis/${analysis.id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <section>
      <div
        onClick={() => !busy && input.current.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          send(e.dataTransfer.files[0]);
        }}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition ${
          dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <p className="text-lg font-medium">{busy ? "Uploading…" : "Drop an image, video or audio file"}</p>
        <p className="mt-1 text-sm text-slate-500">or click to choose · JPG, PNG, WEBP · MP4, MOV, AVI · WAV, MP3, M4A, OGG (WhatsApp voice notes)</p>
        <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={(e) => send(e.target.files[0])} />
      </div>
      {error && <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
      <p className="mt-6 text-xs text-slate-500">
        Image checks: AI-image model, face-swap model, metadata, error level analysis, frequency analysis. Audio checks: AI-voice model, splice check. Video
        checks: face-swap and AI-image models on sampled frames, plus all audio checks on the sound track.
      </p>
    </section>
  );
}
