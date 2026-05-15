const DEFAULT_BACKEND_URL = "http://localhost:8000";

export function getBackendUrl(): string {
  const raw = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL;
  return raw.replace(/\/+$/, "");
}

export function resolveBackendUrl(backendUrl: string, pathOrUrl: string): string {
  if (!pathOrUrl) return pathOrUrl;
  return pathOrUrl.startsWith("/") ? `${backendUrl}${pathOrUrl}` : pathOrUrl;
}
