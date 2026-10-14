import { useEffect, useState } from "react";

// Tiny hash router: "#/" -> upload, "#/analysis/<id>" -> result, "#/history" -> past checks.
export function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  const m = hash.match(/^#\/analysis\/([\w-]+)$/);
  if (m) return { page: "analysis", id: m[1] };
  if (hash === "#/history") return { page: "history" };
  return { page: "upload" };
}

export const goTo = (path) => {
  window.location.hash = path;
};
