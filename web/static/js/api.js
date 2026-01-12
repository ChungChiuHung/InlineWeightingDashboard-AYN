export async function getFishTypes() {
  const r = await fetch('/api/fish-types');
  return await r.json();
}

export async function writeTag(tag, value) {
  return fetch(`/write/${tag}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ value })
  });
}
