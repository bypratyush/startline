// Thin fetch wrapper. The browser always talks to /api on its own origin:
// Vite proxies it in development, nginx in Docker, the Ingress in Kubernetes.

export class ApiError extends Error {
  constructor(status, message, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function messageFrom(body, status) {
  if (!body) return `Request failed (${status})`;
  const d = body.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) {
    // pydantic validation errors: "body.phone: enter a 10-digit ..."
    return d
      .map((e) => {
        const field = (e.loc || []).filter((p) => p !== "body").join(".");
        const msg = String(e.msg || "").replace(/^Value error, /, "");
        return field ? `${field.replaceAll("_", " ")}: ${msg}` : msg;
      })
      .join(" · ");
  }
  return `Request failed (${status})`;
}

async function request(method, path, body, { signal } = {}) {
  const res = await fetch(path, {
    method,
    signal,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) throw new ApiError(res.status, messageFrom(data, res.status), data?.detail);
  return data;
}

export function qs(params) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x));
    else sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  get: (path, opts) => request("GET", path, null, opts),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),
};
