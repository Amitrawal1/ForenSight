import { useEffect, useState } from "react";
import { getHealth } from "./lib/api.js";
import UploadPage from "./pages/UploadPage.jsx";

export default function App() {
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    getHealth()
      .then((h) => setApiStatus(h.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <h1 className="text-xl font-bold">ForenSight</h1>
          <span className="text-sm text-slate-500">API: {apiStatus}</span>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-10">
        <UploadPage />
      </main>
    </div>
  );
}
