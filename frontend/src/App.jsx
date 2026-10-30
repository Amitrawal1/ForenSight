import { useEffect, useState } from "react";
import { getHealth } from "./lib/api.js";
import { goTo, useHashRoute } from "./lib/useHashRoute.js";
import UploadPage from "./pages/UploadPage.jsx";
import AnalysisPage from "./pages/AnalysisPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

// Our logo: a thick ring with a dot in the middle, like a camera lens.
function LensMark() {
  return (
    <svg viewBox="0 0 32 32" className="h-9 w-9 shrink-0 sm:h-11 sm:w-11" aria-hidden="true">
      <circle cx="16" cy="16" r="11.5" fill="none" stroke="#14202E" strokeWidth="7" />
      <circle cx="16" cy="16" r="4" fill="#0E6E8C" />
    </svg>
  );
}

// One pill in the top menu. The page you are on is navy, the others are teal.
function NavPill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`lift rounded-full px-3 py-1.5 text-sm font-semibold whitespace-nowrap text-white sm:px-5 sm:py-2 sm:text-lg ${
        active ? "bg-navy" : "bg-teal"
      }`}
    >
      {children}
    </button>
  );
}

// Small dot showing if the API is reachable. It differs by shape as well as colour,
// because red and green are kept for verdicts only.
function ApiStatus({ status }) {
  const dot = status === "ok" ? "bg-teal" : status === "unreachable" ? "border-2 border-navy bg-transparent" : "bg-line";
  return (
    <span role="status" title={`API: ${status}`} className="flex items-center">
      <span className={`block h-3 w-3 rounded-full ${dot}`} />
      <span className="sr-only">API status: {status}</span>
    </span>
  );
}

export default function App() {
  const route = useHashRoute();
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    getHealth()
      .then((h) => setApiStatus(h.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="relative z-10 flex items-center justify-between gap-2 px-4 py-4 sm:px-8 sm:py-5">
        <button onClick={() => goTo("/")} className="flex items-center gap-2 rounded-full text-lg font-bold tracking-tight sm:gap-3 sm:text-2xl">
          <LensMark />
          {/* On the narrowest phones only the mark shows, so the menu still fits. */}
          <span className="max-[359px]:sr-only">ForenSight</span>
        </button>
        <nav aria-label="Main" className="flex items-center gap-1.5 sm:gap-2">
          <NavPill active={route.page === "upload"} onClick={() => goTo("/")}>
            New check
          </NavPill>
          <NavPill active={route.page === "history"} onClick={() => goTo("/history")}>
            History
          </NavPill>
          <span className="ml-1 sm:ml-2">
            <ApiStatus status={apiStatus} />
          </span>
        </nav>
      </header>

      {/* Pages choose their own width, so the landing page can run edge to edge. */}
      <main className="min-w-0 flex-1">
        {route.page === "analysis" && (
          <div className="mx-auto w-full max-w-[1280px] px-4 py-8 sm:px-8">
            <AnalysisPage id={route.id} />
          </div>
        )}
        {route.page === "history" && <HistoryPage />}
        {route.page === "upload" && <UploadPage />}
      </main>

      <footer className="bg-navy px-4 py-8 text-center text-white sm:px-8">
        <p className="text-lg">ForenSight supports human decisions and does not replace them.</p>
      </footer>
    </div>
  );
}
