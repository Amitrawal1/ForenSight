import { useRef, useState } from "react";
import MarkPattern from "../components/ui/MarkPattern.jsx";
import Pill from "../components/ui/Pill.jsx";
import ProgressBar from "../components/ui/ProgressBar.jsx";
import { uploadFile } from "../lib/api.js";
import { goTo } from "../lib/useHashRoute.js";
import { VERDICTS } from "../lib/verdicts.js";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.wav,.mp3,.m4a,.ogg,.opus";

const STEPS = [
  { title: "Upload", text: "Drop an image, video or audio file. ForenSight reads the file's own bytes to learn its type, not its name." },
  { title: "Prepare", text: "Video is cut down to sample frames spread evenly over its length. Sound is decoded into one simple format." },
  { title: "Nine checks", text: "The checks that fit the file run separately. Each one reports what it found and how much it can be trusted." },
  { title: "Verdict and reasons", text: "The results are combined into one verdict with its top reasons. If the evidence is unclear, it does not guess." },
];

// These sentences match the summaries the backend writes on the result page.
const VERDICT_MEANINGS = [
  { key: "likely_authentic", text: "No significant signs of AI generation or manipulation were found." },
  { key: "ai_generated", text: "This content appears to have been created by an AI model." },
  { key: "manipulated", text: "This content appears to be real but partly changed or edited." },
  { key: "inconclusive", text: "The evidence is weak or mixed, so ForenSight does not make a call." },
];

const CHECKS = [
  { media: "Image", items: ["AI-image model", "Face-swap model", "File metadata", "Error Level Analysis", "Frequency analysis"] },
  { media: "Video", items: ["Face-swap model on sampled frames", "AI-image model on sampled frames", "File metadata", "AI-voice model on the sound track", "Audio splice check on the sound track"] },
  { media: "Audio", items: ["AI-voice model", "Audio splice check"] },
];

// A word of the giant wordmark. The thick stroke with round joins softens the letter corners.
function WordmarkWord({ word, viewBox }) {
  return (
    <svg viewBox={viewBox} className="wordmark-word" aria-hidden="true">
      <text x="0" y="146" fontSize="200" fontWeight="700" letterSpacing="7" fill="#14202E" stroke="#14202E" strokeWidth="9" strokeLinejoin="round">
        {word}
      </text>
    </svg>
  );
}

// The two pill lines of the hero statement. Used in two places because the layout changes with screen size.
function Statement({ className = "" }) {
  return (
    <p className={`hero-statement flex shrink-0 flex-col items-start gap-[0.14em] leading-[1.15] font-semibold tracking-tight ${className}`}>
      <Pill tone="teal" className="whitespace-nowrap">Is this real?</Pill>
      <span className="flex items-center gap-[0.14em]">
        <span className="block h-[1.39em] w-[1.39em] shrink-0 rounded-full bg-white" aria-hidden="true" />
        <Pill tone="white" className="whitespace-nowrap">Find out why</Pill>
      </span>
    </p>
  );
}

// Upload box: drag and drop or click to choose. Shows a progress bar while sending.
function DropZone() {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pct, setPct] = useState(null); // null until the first progress update arrives
  const [error, setError] = useState(null);

  async function send(file) {
    if (!file || busy) return;
    setBusy(true);
    setPct(null);
    setError(null);
    try {
      const analysis = await uploadFile(file, (p) => setPct(p));
      goTo(`/analysis/${analysis.id}`);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <div>
      <div
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
        className={`rounded-card border border-navy transition-colors ${dragging ? "bg-teal text-white" : "bg-white"}`}
      >
        {busy ? (
          <div className="px-6 py-10 sm:px-12 sm:py-14">
            <ProgressBar percent={pct ?? 0} indeterminate={pct === null} label={pct === 100 ? "Sent. Starting the checks" : "Uploading your file"} />
          </div>
        ) : (
          <button
            type="button"
            onClick={() => input.current.click()}
            className="group flex w-full flex-col items-start gap-5 rounded-card px-6 py-7 text-left sm:px-12 sm:py-10 lg:flex-row lg:py-14 lg:items-center lg:justify-between lg:gap-10"
          >
            <span className="block">
              <span className="block text-3xl leading-[1.05] font-semibold tracking-tight sm:text-5xl">Drop an image, video or audio file</span>
              <span className={`mt-3 block text-base ${dragging ? "text-white" : "text-muted"}`}>
                JPG, PNG, WEBP · MP4, MOV, AVI · WAV, MP3, M4A, OGG (WhatsApp voice notes)
              </span>
            </span>
            <span className={`lift shrink-0 rounded-full px-7 py-3 text-xl font-semibold group-hover:-translate-y-0.5 ${dragging ? "bg-white text-navy" : "bg-teal text-white"}`}>
              Choose a file
            </span>
          </button>
        )}
        {/* Clear the value afterwards, so the same file can be picked again after an error. */}
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            send(e.target.files[0]);
            e.target.value = "";
          }}
        />
      </div>
      {error && (
        <p role="alert" className="mt-3 rounded-3xl border border-navy bg-white px-6 py-4 font-medium">
          {error}
        </p>
      )}
    </div>
  );
}

// Section heading: a big solid pill.
function SectionTitle({ children, tone = "teal" }) {
  return (
    <h2 className="text-4xl leading-tight font-semibold tracking-tight sm:text-5xl">
      <Pill tone={tone}>{children}</Pill>
    </h2>
  );
}

// Landing page: giant wordmark and upload box first, then what ForenSight does and how.
export default function UploadPage() {
  return (
    <div className="overflow-x-clip">
      <section className="relative px-4 pb-10 sm:px-8">
        {/* The word images are hidden from screen readers, so the real heading is this hidden text. */}
        <h1 className="sr-only">ForenSight</h1>

        <div className="flex items-center justify-between gap-6">
          <WordmarkWord word="FOREN" viewBox="-5 0 714 154" />
          {/* The pattern fills the empty space beside the first word, clear of the menu. */}
          <MarkPattern className="wordmark-word hidden min-w-0 shrink lg:block" />
        </div>
        <div className="mt-2 flex items-center justify-between gap-4 lg:mt-3">
          <Statement className="hidden lg:flex" />
          <div className="ml-auto">
            <WordmarkWord word="SIGHT" viewBox="-5 0 644 154" />
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between gap-2 lg:hidden">
          <Statement />
          <MarkPattern layout="small" className="w-24 min-w-0 shrink max-[359px]:hidden sm:w-40" />
        </div>

        <div className="relative mt-6">
          <DropZone />
        </div>
      </section>

      <section className="px-4 py-10 sm:px-8 sm:py-16">
        <SectionTitle>How it works</SectionTitle>
        <ol className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {STEPS.map((step, i) => (
            <li key={step.title} className="rounded-card border border-navy bg-white p-7 sm:p-8">
              <span className="block text-5xl font-extrabold tracking-tight text-teal" aria-hidden="true">
                {i + 1}
              </span>
              <h3 className="mt-8 text-2xl font-semibold tracking-tight sm:text-3xl">{step.title}</h3>
              <p className="mt-3 text-lg leading-snug text-muted">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="bg-teal px-4 py-14 text-white sm:px-8 sm:py-20">
        <p className="mx-auto max-w-6xl text-center text-4xl leading-[1.02] font-bold tracking-tight sm:text-5xl lg:text-6xl">A reason matters more than a score.</p>
      </section>

      <section className="px-4 py-10 sm:px-8 sm:py-16">
        <SectionTitle tone="navy">Four verdicts</SectionTitle>
        <ul className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {VERDICT_MEANINGS.map(({ key, text }) => (
            <li key={key} className="rounded-card border border-navy bg-white p-7 sm:p-8">
              <span className={`block h-10 w-10 rounded-full ${VERDICTS[key].bar}`} aria-hidden="true" />
              <h3 className="mt-8 text-2xl font-semibold tracking-tight sm:text-3xl">{VERDICTS[key].label}</h3>
              <p className="mt-3 text-lg leading-snug text-muted">{text}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="px-4 pb-20 sm:px-8 sm:pb-28">
        <SectionTitle tone="white">Nine checks</SectionTitle>
        <p className="mt-6 max-w-3xl text-xl leading-snug text-muted">Only the checks that fit your file run. File metadata and the two audio checks work on more than one media type.</p>
        <div className="mt-10 grid gap-4 lg:grid-cols-3">
          {CHECKS.map((group) => (
            <div key={group.media} className="rounded-card border border-navy bg-white p-7 sm:p-8">
              <h3 className="text-3xl font-semibold tracking-tight">{group.media}</h3>
              <ul className="mt-5">
                {group.items.map((item) => (
                  <li key={item} className="border-t border-line py-3 text-lg leading-snug">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
