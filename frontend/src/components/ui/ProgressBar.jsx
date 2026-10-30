// Thick pill-shaped progress bar.
// percent: 0 to 100. label: short text above the bar.
// indeterminate: true when we do not know how far along the work is, so it shows a sliding block and no number.
export default function ProgressBar({ percent = 0, label, indeterminate = false }) {
  const value = Math.min(100, Math.max(0, Math.round(Number(percent) || 0)));

  // Screen readers read these values. Without a known value, aria-valuenow must be left out.
  const aria = indeterminate ? {} : { "aria-valuenow": value };

  return (
    <div className="w-full">
      {(label || !indeterminate) && (
        <div className="mb-2 flex items-baseline justify-between gap-4 font-semibold text-navy">
          <span>{label}</span>
          {!indeterminate && <span className="text-2xl tabular-nums tracking-tight">{value}%</span>}
        </div>
      )}
      <div
        role="progressbar"
        aria-label={label || "Progress"}
        aria-valuemin={0}
        aria-valuemax={100}
        {...aria}
        className="h-6 w-full overflow-hidden rounded-full border border-navy bg-white"
      >
        {indeterminate ? (
          <div className="progress-slide h-full w-1/3 rounded-full bg-teal" />
        ) : (
          <div className="h-full rounded-full bg-teal transition-[width] duration-200" style={{ width: `${value}%` }} />
        )}
      </div>
    </div>
  );
}
