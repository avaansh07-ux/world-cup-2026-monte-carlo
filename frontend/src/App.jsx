import { useEffect, useState } from "react";
import { fetchTeams, previewInjury, runSimulation } from "./api";

const defaultSimulation = {
  probabilities: [],
  scorelines: [],
  finalists: [],
  bracketExample: [],
  iterations: 10000,
};

export default function App() {
  const [teams, setTeams] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [injuryPreview, setInjuryPreview] = useState(null);
  const [injuries, setInjuries] = useState([]);
  const [simulation, setSimulation] = useState(defaultSimulation);
  const [iterations, setIterations] = useState(10000);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadTeams() {
      try {
        const payload = await fetchTeams();
        setTeams(payload.teams);
        if (payload.teams.length > 0) {
          setSelectedTeamId(String(payload.teams[0].id));
          setSelectedTeam(payload.teams[0]);
        }
      } catch (loadError) {
        setError("Could not load team data from the Flask API.");
      } finally {
        setLoading(false);
      }
    }

    loadTeams();
  }, []);

  useEffect(() => {
    const team = teams.find((entry) => String(entry.id) === selectedTeamId) || null;
    setSelectedTeam(team);
    setInjuryPreview(null);
    setInjuries([]);
  }, [selectedTeamId, teams]);

  async function handleInjury(playerName) {
    if (!selectedTeam) {
      return;
    }
    const existing = injuries.some((item) => item.playerName === playerName);
    if (existing) {
      const next = injuries.filter((item) => item.playerName !== playerName);
      setInjuries(next);
      setInjuryPreview(null);
      return;
    }

    const next = [...injuries, { teamId: selectedTeam.id, playerName }];
    setInjuries(next);
    const payload = await previewInjury({ teamId: selectedTeam.id, playerName });
    setInjuryPreview(payload.team);
  }

  async function handleSimulation() {
    setRunning(true);
    setError("");
    try {
      const payload = await runSimulation({
        selectedTeamId,
        iterations,
        injuries,
      });
      setSimulation(payload);
    } catch (simulationError) {
      setError("Simulation failed. Make sure the backend is running on port 5001.");
    } finally {
      setRunning(false);
    }
  }

  const displayTeam = injuryPreview || selectedTeam;

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">FIFA WORLD CUP 2026</p>
          <h1>Monte Carlo matchday drama, rendered like a tournament night.</h1>
          <p className="lede">
            Simulate title paths, scoreline chaos, and knockout survival odds with a
            Flask model built for football-first storytelling.
          </p>
        </div>
        <div className="hero-card">
          <span>Iterations</span>
          <strong>{iterations.toLocaleString()}</strong>
          <input
            type="range"
            min="1000"
            max="50000"
            step="1000"
            value={iterations}
            onChange={(event) => setIterations(Number(event.target.value))}
          />
          <button onClick={handleSimulation} disabled={running || loading}>
            {running ? "Running Simulation..." : "Run Tournament"}
          </button>
        </div>
      </section>

      {error ? <p className="error-banner">{error}</p> : null}

      <section className="grid">
        <article className="panel selection-panel">
          <div className="panel-heading">
            <span>Featured Team</span>
            <select
              value={selectedTeamId}
              onChange={(event) => setSelectedTeamId(event.target.value)}
              disabled={loading}
            >
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </div>

          {displayTeam ? (
            <div className="team-card">
              <h2>{displayTeam.name}</h2>
              <p>
                Group {displayTeam.group} · {displayTeam.confederation}
              </p>
              <div className="metric-row">
                <div>
                  <span>Attack</span>
                  <strong>{displayTeam.attack}</strong>
                </div>
                <div>
                  <span>Defense</span>
                  <strong>{displayTeam.defense}</strong>
                </div>
                <div>
                  <span>Rating</span>
                  <strong>{displayTeam.rating}</strong>
                </div>
              </div>

              <div className="player-list">
                <h3>Toggle injuries</h3>
                {selectedTeam?.players?.map((player) => {
                  const active = injuries.some((item) => item.playerName === player.name);
                  return (
                    <button
                      key={player.name}
                      className={active ? "player-chip active" : "player-chip"}
                      onClick={() => handleInjury(player.name)}
                    >
                      {player.name} · {player.rating}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            <p>Loading team profile...</p>
          )}
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span>Title Odds</span>
            <span>Top 6</span>
          </div>
          <div className="probability-list">
            {simulation.probabilities.slice(0, 6).map((entry) => (
              <div key={entry.team} className="probability-row">
                <div>
                  <strong>{entry.team}</strong>
                  <small>
                    Final {Math.round(entry.finalProbability * 100)}% · Semi{" "}
                    {Math.round(entry.semiProbability * 100)}%
                  </small>
                </div>
                <span>{Math.round(entry.winProbability * 100)}%</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span>Bracket Snapshot</span>
            <span>1 sample path</span>
          </div>
          <div className="bracket-list">
            {simulation.bracketExample.map((match) => (
              <div key={`${match.round}-${match.home}-${match.away}`} className="bracket-row">
                <p>{match.round}</p>
                <strong>
                  {match.home} {match.score} {match.away}
                </strong>
                <span>{match.winner} advance</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <span>Final Scorelines</span>
            <span>Most frequent</span>
          </div>
          <div className="scoreline-grid">
            {simulation.scorelines.map((entry) => (
              <div key={entry.score} className="score-chip">
                <strong>{entry.score}</strong>
                <span>{Math.round(entry.probability * 100)}%</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
