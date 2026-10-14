import { useEffect, useState } from "react";
import { getHealth } from "./lib/api.js";
import { goTo, useHashRoute } from "./lib/useHashRoute.js";
import UploadPage from "./pages/UploadPage.jsx";
import AnalysisPage from "./pages/AnalysisPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

export default function App() {
  const route = useHashRoute();
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    getHealth()
      .then((h) => setApiStatus(h.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <button onClick={() => goTo("/")} className="text-xl font-bold">
            ForenSight
          </button>
          <nav className="flex items-center gap-4 text-sm">
            <button onClick={() => goTo("/")} className={route.page === "upload" ? "font-semibold" : "text-slate-600 hover:text-slate-900"}>
              New check
            </button>
            <button onClick={() => goTo("/history")} className={route.page === "history" ? "font-semibold" : "text-slate-600 hover:text-slate-900"}>
              History
            </button>
            <span className={apiStatus === "ok" ? "text-emerald-600" : "text-rose-600"} title={`API: ${apiStatus}`}>
              ●
            </span>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-10">
        {route.page === "analysis" && <AnalysisPage id={route.id} />}
        {route.page === "history" && <HistoryPage />}
        {route.page === "upload" && <UploadPage />}
      </main>
    </div>
  );
}
