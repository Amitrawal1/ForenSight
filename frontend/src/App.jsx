import { useEffect, useState } from "react";
import { getHealth } from "./lib/api.js";
import { goTo, useHashRoute } from "./lib/useHashRoute.js";
import UploadPage from "./pages/UploadPage.jsx";
import AnalysisPage from "./pages/AnalysisPage.jsx";

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
          <span className="text-sm text-slate-500">API: {apiStatus}</span>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-10">
        {route.page === "analysis" ? <AnalysisPage id={route.id} /> : <UploadPage />}
      </main>
    </div>
  );
}
