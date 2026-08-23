export async function fetchHealth() {
  const res = await fetch("/api/health");
  return res.json();
}

export async function fetchStarters() {
  const res = await fetch("/api/starters");
  const body = await res.json();
  return body.domains;
}

export async function sendChat(messages) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.json();
}
