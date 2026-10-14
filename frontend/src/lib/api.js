export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request(path, options) {
  const res = await fetch(`${API_URL}${path}`, options);
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const getHealth = () => request("/api/health");

export function uploadFile(file) {
  const body = new FormData();
  body.append("file", file);
  return request("/api/analyses", { method: "POST", body });
}

export const getAnalysis = (id) => request(`/api/analyses/${id}`);

export const artifactUrl = (id, name) => `${API_URL}/api/analyses/${id}/artifacts/${name}`;
export const originalUrl = (id) => `${API_URL}/api/analyses/${id}/original`;
