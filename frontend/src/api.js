const isLocal =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  (isLocal ? "http://127.0.0.1:5001/api" : "/_/backend/api");

async function readJson(response) {
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchGroups() {
  return readJson(await fetch(`${API_BASE_URL}/groups`));
}

export async function fetchTeams() {
  return readJson(await fetch(`${API_BASE_URL}/teams`));
}

export async function fetchTeam(teamId) {
  return readJson(await fetch(`${API_BASE_URL}/team/${teamId}`));
}

export async function generateSquads() {
  return readJson(
    await fetch(`${API_BASE_URL}/generate-squads`, {
      method: "POST",
    }),
  );
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
    await fetch(`${API_BASE_URL}/injuries`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function simulateMatch(payload) {
  return readJson(
    await fetch(`${API_BASE_URL}/simulate-match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}

export async function compareTeams(payload) {
  return readJson(
    await fetch(`${API_BASE_URL}/compare-teams`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
}
