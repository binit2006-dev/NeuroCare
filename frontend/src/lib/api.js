import axios from "axios";

export const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API_BASE, withCredentials: true });

export async function exchangeSession(sessionId) {
  const { data } = await api.post("/auth/session", { session_id: sessionId });
  return data;
}

export async function fetchMe() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function logoutApi() {
  await api.post("/auth/logout");
}

export async function fetchMyScans() {
  const { data } = await api.get("/my-scans");
  return data;
}

export async function predictMRI(file, location) {
  const fd = new FormData();
  fd.append("mri", file);
  fd.append("location", location || "");
  const { data } = await api.post("/predict", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchAdvice(scan) {
  const { data } = await api.post("/advice", {
    scan_id: scan.id,
    tumor_type: scan.tumor_type,
    confidence: scan.confidence,
    location: scan.location || "",
    tumor_detected: scan.tumor_detected,
  });
  return data;
}

export async function fetchDownloads() {
  const { data } = await api.get("/downloads");
  return data;
}

export async function fetchModelStatus() {
  const { data } = await api.get("/model-status");
  return data;
}

export function downloadUrl(filename) {
  return `${API_BASE}/downloads/${encodeURIComponent(filename)}`;
}
