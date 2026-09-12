// Shared helpers used by index.html, create.html, ticket.html.
const API = "/api";

function statusSlug(status) {
  return status.toLowerCase().replace(/\s+/g, "-");
}

function badge(text, cls) {
  return `<span class="badge ${cls}">${text}</span>`;
}

function statusBadge(status) {
  return badge(status, `status-${statusSlug(status)}`);
}

function priorityBadge(priority) {
  return badge(priority, `priority-${priority.toLowerCase()}`);
}

function formatDate(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function qs(name) {
  return new URLSearchParams(window.location.search).get(name);
}

async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}
