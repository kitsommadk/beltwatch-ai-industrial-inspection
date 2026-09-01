const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  health: () => request("/health"),
  system: () => request("/system"),
  session: () => request("/session"),
  events: () => request("/events"),
  summary: () => request("/summary"),
  evidence: (limit = 100) => request(`/evidence?limit=${limit}`),
  evidenceSummary: () => request("/evidence/summary"),
  captureEvidence: (camera, measured_span_px) => request("/evidence/capture", {
    method: "POST",
    body: JSON.stringify({ camera, measured_span_px }),
  }),
  start: (data) => request("/session/start", { method: "POST", body: JSON.stringify(data) }),
  pause: () => request("/session/pause", { method: "POST" }),
  progress: (delta_ft = 12) => request("/session/progress", { method: "POST", body: JSON.stringify({ delta_ft }) }),
  detect: (kind) => request("/events/simulate", { method: "POST", body: JSON.stringify({ kind }) }),
  review: (id, status, note = "") => request(`/events/${id}/review`, { method: "POST", body: JSON.stringify({ status, note }) }),
};
