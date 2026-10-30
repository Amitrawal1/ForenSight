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

// Uses XMLHttpRequest because fetch cannot report how many bytes were sent so far.
// onProgress (optional) receives the upload percent, 0 to 100.
export function uploadFile(file, onProgress) {
  const body = new FormData();
  body.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/analyses`);

    xhr.upload.onprogress = (event) => {
      if (onProgress && event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        let detail = `Request failed (${xhr.status})`;
        try {
          detail = JSON.parse(xhr.responseText).detail ?? detail;
        } catch {
          /* not JSON */
        }
        reject(new Error(detail));
        return;
      }
      try {
        resolve(JSON.parse(xhr.responseText));
      } catch (err) {
        reject(err);
      }
    };

    // Same kind of error fetch gives when the server cannot be reached
    xhr.onerror = () => reject(new TypeError("Failed to fetch"));
    xhr.onabort = () => reject(new TypeError("Failed to fetch"));

    xhr.send(body);
  });
}

export const getAnalysis = (id) => request(`/api/analyses/${id}`);

export const artifactUrl = (id, name) => `${API_URL}/api/analyses/${id}/artifacts/${name}`;
export const originalUrl = (id) => `${API_URL}/api/analyses/${id}/original`;

export const listAnalyses = () => request("/api/analyses");
export const deleteAnalysis = (id) => request(`/api/analyses/${id}`, { method: "DELETE" });
export const reportUrl = (id) => `${API_URL}/api/analyses/${id}/report`;
