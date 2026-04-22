const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5001";

async function readJson(response) {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchTeams() {
  return readJson(await fetch(`${API_BASE_URL}/teams`));
}

export async function runSimulation(payload) {
  return readJson(
    await fetch(`${API_BASE_URL}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function previewInjury(payload) {
  return readJson(
    await fetch(`${API_BASE_URL}/injury`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
