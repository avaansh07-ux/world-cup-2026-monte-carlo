import { useEffect, useState } from "react";
import {
  fetchGroups,
  fetchTeam,
  fetchTeams,
  generateSquads,
  previewInjury,
  runSimulation,
  simulateMatch,
} from "./api";
import { PLAYER_IMAGES } from "./playerImages";

const simulationOptions = [
  { label: "250", value: 250 },
  { label: "1,000", value: 1000 },
  { label: "5,000", value: 5000 },
  { label: "10,000 slower but more stable", value: 10000 },
];

const emptySimulation = {
  probabilities: [],
  mostCommonScorelines: [],
  sampleBracket: [],
  topScorers: [],
  groups: [],
  iterations: 1000,
  simulationRunId: null,
};

const tabs = [
  "Overview",
  "Groups",
  "Team Lineup",
  "Predicted Bracket Path",
  "X-Factors",
];

const hostNations = [
  {
    team: "Canada",
    flag: "CA",
    group: "B",
  },
  {
    team: "Mexico",
    flag: "MX",
    group: "A",
  },
  {
    team: "United States",
    flag: "US",
    group: "D",
  },
];

const hostLocations = {
  Canada: ["Toronto", "Vancouver"],
  Mexico: ["Mexico City", "Guadalajara", "Monterrey"],
  "United States": [
    "Atlanta",
    "Boston",
    "Dallas",
    "Houston",
    "Kansas City",
    "Los Angeles",
    "Miami",
    "New York/New Jersey",
    "Philadelphia",
    "San Francisco Bay Area",
    "Seattle",
  ],
};

const teamXFactorMap = {
  France: {
    player: "Kylian Mbappé",
    label: "Kylian Mbappé",
    position: "Forward",
    reason: "Game-breaking pace and finishing make France's attack elite.",
  },
  England: {
    player: "Jude Bellingham",
    label: "Jude Bellingham",
    position: "Midfielder",
    reason: "Drives England through midfield with scoring and control.",
  },
  Spain: {
    player: "Lamine Yamal",
    label: "Lamine Yamal",
    position: "Forward",
    reason: "A creative wide threat who can tilt tight knockout games.",
  },
  Brazil: {
    player: "Vinícius Júnior",
    label: "Vinícius Júnior",
    position: "Forward",
    reason: "One of the best one-on-one attackers in the tournament.",
  },
  Argentina: {
    player: "Lionel Messi",
    label: "Lionel Messi",
    position: "Forward",
    reason: "Still Argentina's main creator and late-game difference maker.",
  },
  Portugal: {
    player: "Bruno Fernandes",
    label: "Bruno Fernandes",
    position: "Midfielder",
    reason: "Portugal's creative engine and set-piece threat.",
  },
  Germany: {
    player: "Florian Wirtz",
    label: "Florian Wirtz",
    position: "Midfielder",
    reason: "Creative force between the lines.",
  },
  Netherlands: {
    player: "Virgil van Dijk",
    label: "Virgil van Dijk",
    position: "Defender",
    reason: "Anchors one of the strongest defensive cores.",
  },
  Morocco: {
    player: "Achraf Hakimi",
    label: "Achraf Hakimi",
    position: "Right Back",
    reason: "Two-way fullback who drives Morocco's transition threat.",
  },
  Norway: {
    player: "Erling Haaland",
    label: "Erling Haaland",
    position: "Forward",
    reason: "Elite penalty-box finishing keeps Norway dangerous in any draw.",
  },
  Belgium: {
    player: "Kevin De Bruyne",
    label: "Kevin De Bruyne",
    position: "Midfielder",
    reason: "Still the cleanest chance creator in Belgium's side.",
  },
  Canada: {
    player: "Alphonso Davies",
    label: "Alphonso Davies",
    position: "Left Back",
    reason: "Explosive carrying gives Canada a unique transition weapon.",
  },
};

const xFactorCards = [
  ["France", "Kylian Mbappé", "Forward", "Game-breaking pace and finishing make France's attack elite."],
  ["England", "Jude Bellingham", "Midfielder", "Drives England through midfield with scoring and control."],
  ["England", "Harry Kane", "Forward", "Elite finishing and link-up play give England a reliable goal source."],
  ["Spain", "Lamine Yamal", "Forward", "A creative wide threat who can tilt tight knockout games."],
  ["Spain", "Pedri", "Midfielder", "Controls tempo and chance creation for Spain."],
  ["Brazil", "Vinícius Júnior", "Forward", "One of the best one-on-one attackers in the tournament."],
  ["Argentina", "Lionel Messi", "Forward", "Still Argentina's main creator and late-game difference maker."],
  ["Argentina", "Julián Álvarez", "Forward", "Pressing, movement, and finishing add depth to Argentina's attack."],
  ["Portugal", "Bruno Fernandes", "Midfielder", "Portugal's creative engine and set-piece threat."],
  ["Portugal", "Cristiano Ronaldo", "Forward", "Still a major box threat and finishing option."],
  ["Germany", "Florian Wirtz", "Midfielder", "Creative force between the lines."],
  ["Germany", "Jamal Musiala", "Midfielder", "Elite dribbling and chance creation."],
  ["Netherlands", "Virgil van Dijk", "Defender", "Anchors one of the strongest defensive cores."],
  ["Morocco", "Achraf Hakimi", "Right Back", "Two-way fullback who drives Morocco's transition threat."],
  ["Norway", "Erling Haaland", "Forward", "Elite penalty-box finishing keeps Norway dangerous in any draw."],
  ["Uruguay", "Federico Valverde", "Midfielder", "Adds range, pressing, and late-box production."],
  ["Belgium", "Kevin De Bruyne", "Midfielder", "Still the cleanest chance creator in Belgium's side."],
  ["Croatia", "Luka Modrić", "Midfielder", "Still sets rhythm and solves pressure phases."],
  ["Senegal", "Sadio Mané", "Forward", "Direct running and finishing can swing knockout ties."],
  ["Canada", "Alphonso Davies", "Left Back", "Explosive carrying gives Canada a unique transition weapon."],
  ["Colombia", "Luis Díaz", "Forward", "Direct dribbling and transition threat make him Colombia's sharpest edge."],
];

function normalizeName(value) {
  return (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function slugifyName(value) {
  return (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function teamSlug(value) {
  return slugifyName(value);
}

function initials(value) {
  return (value || "WC")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function bracketByRound(matches) {
  return matches.reduce((accumulator, match) => {
    accumulator[match.round] = [...(accumulator[match.round] || []), match];
    return accumulator;
  }, {});
}

function bootReason(entry) {
  const role =
    entry.position === "ST" || entry.position === "CF"
      ? "Natural central finisher"
      : entry.position === "LW" || entry.position === "RW"
        ? "Explosive wide scorer"
        : "High-touch creator with scoring volume";
  return `${role}. ${entry.country} project to play enough matches to keep the goal total live.`;
}

const formationCoordinates = {
  "4-3-3": [
    { x: 50, y: 88 },
    { x: 78, y: 70 },
    { x: 60, y: 66 },
    { x: 40, y: 66 },
    { x: 22, y: 70 },
    { x: 50, y: 54 },
    { x: 34, y: 46 },
    { x: 66, y: 46 },
    { x: 82, y: 24 },
    { x: 50, y: 16 },
    { x: 18, y: 24 }
  ],
  "4-4-2": [
    { x: 50, y: 88 },
    { x: 78, y: 70 },
    { x: 60, y: 66 },
    { x: 40, y: 66 },
    { x: 22, y: 70 },
    { x: 80, y: 48 },
    { x: 58, y: 50 },
    { x: 42, y: 50 },
    { x: 20, y: 48 },
    { x: 40, y: 20 },
    { x: 60, y: 20 }
  ],
  "4-2-3-1": [
    { x: 50, y: 88 },
    { x: 78, y: 70 },
    { x: 60, y: 66 },
    { x: 40, y: 66 },
    { x: 22, y: 70 },
    { x: 42, y: 54 },
    { x: 58, y: 54 },
    { x: 80, y: 34 },
    { x: 50, y: 30 },
    { x: 20, y: 34 },
    { x: 50, y: 16 }
  ],
  "3-4-2-1": [
    { x: 50, y: 88 },
    { x: 68, y: 68 },
    { x: 50, y: 64 },
    { x: 32, y: 68 },
    { x: 80, y: 48 },
    { x: 42, y: 48 },
    { x: 58, y: 48 },
    { x: 20, y: 48 },
    { x: 40, y: 28 },
    { x: 60, y: 28 },
    { x: 50, y: 14 }
  ],
  "3-4-3": [
    { x: 50, y: 88 },
    { x: 68, y: 68 },
    { x: 50, y: 64 },
    { x: 32, y: 68 },
    { x: 80, y: 48 },
    { x: 42, y: 48 },
    { x: 58, y: 48 },
    { x: 20, y: 48 },
    { x: 82, y: 22 },
    { x: 50, y: 16 },
    { x: 18, y: 22 }
  ]
};

function playerImageCandidates(player, label, imageOverride) {
  const names = [
    label,
    player?.name,
    player?.player_name,
    player?.short_name,
    player?.long_name,
  ].filter(Boolean);

  const manualMatches = names
    .map((name) => PLAYER_IMAGES[name])
    .filter(Boolean);

  const configMatches = names
    .map((name) => Object.keys(PLAYER_IMAGES).find((key) => normalizeName(key) === normalizeName(name)))
    .filter(Boolean)
    .map((key) => PLAYER_IMAGES[key])
    .filter(Boolean);

  const guessed = names.flatMap((name) => {
    const slug = slugifyName(name);
    return slug
      ? [".webp", ".png", ".jpg", ".jpeg"].map((extension) => `/players/${slug}${extension}`)
      : [];
  });

  return [...new Set([
    imageOverride,
    player?.image_url,
    player?.headshot_path,
    player?.image_path,
    ...manualMatches,
    ...configMatches,
    ...guessed,
  ].filter(Boolean))];
}

function findPlayerByName(players, candidate) {
  const target = normalizeName(candidate);
  return (
    players.find((player) =>
      [player.short_name, player.long_name, player.player_name].some(
        (value) => normalizeName(value) === target,
      ),
    ) || null
  );
}

function PlayerVisual({
  player,
  label,
  imageOverride,
  className = "avatar-image",
  fallbackClass = "avatar-fallback",
}) {
  const candidates = playerImageCandidates(player, label, imageOverride);
  const [candidateIndex, setCandidateIndex] = useState(0);

  useEffect(() => {
    setCandidateIndex(0);
  }, [candidates.join("|"), label]);

  const src = candidates[candidateIndex];
  if (src) {
    return (
      <img
        className={className}
        src={src}
        alt={label}
        onError={() => {
          console.warn("player-image-failed", { label, src });
          setCandidateIndex((current) => current + 1);
        }}
      />
    );
  }
  return <div className={fallbackClass}>{initials(label)}</div>;
}

function lineupWithCoordinates(startingLineup) {
  const layout = formationCoordinates[startingLineup?.formation] || formationCoordinates["4-3-3"];
  return (startingLineup?.players || []).map((player, index) => ({
    ...player,
    coordinate: layout[index] || { x: 50, y: 50 },
  }));
}

export default function App() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [groups, setGroups] = useState([]);
  const [teams, setTeams] = useState([]);
  const [teamDetail, setTeamDetail] = useState(null);
  const [teamLoading, setTeamLoading] = useState(false);
  const [teamError, setTeamError] = useState("");
  const [selectedTeamId, setSelectedTeamId] = useState("");
  const [iterations, setIterations] = useState(1000);
  const [simulation, setSimulation] = useState(emptySimulation);
  const [injuries, setInjuries] = useState([]);
  const [matchPreview, setMatchPreview] = useState(null);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [squadMessage, setSquadMessage] = useState("");
  const [elapsedTime, setElapsedTime] = useState(null);

  async function refreshData(keepTeamId) {
    const [groupsPayload, teamsPayload] = await Promise.all([fetchGroups(), fetchTeams()]);
    setGroups(groupsPayload.groups || []);
    setTeams(teamsPayload.teams || []);
    setMeta(teamsPayload.meta || null);
    const nextId =
      keepTeamId && teamsPayload.teams.some((team) => team.team_slug === keepTeamId)
        ? keepTeamId
        : teamsPayload.teams[0]?.team_slug || "";
    setSelectedTeamId(nextId);
  }

  useEffect(() => {
    async function loadInitial() {
      try {
        await refreshData();
        setError("");
      } catch {
        setError("Could not load the World Cup 2026 dataset.");
      } finally {
        setLoading(false);
      }
    }

    loadInitial();
  }, []);

  useEffect(() => {
    async function loadSelectedTeam() {
      if (!selectedTeamId) {
        setTeamDetail(null);
        return;
      }
      setTeamLoading(true);
      setTeamError("");
      try {
        const payload = await fetchTeam(selectedTeamId);
        setTeamDetail({
          ...payload,
          squad: payload.squad || [],
          keyPlayers: payload.keyPlayers || [],
          squadMeta: payload.squadMeta || { players: 0, available: 0, estimated: 0 },
          startingLineup: payload.startingLineup || { formation: "4-3-3", players: [] },
        });
      } catch {
        const fallbackTeam = teams.find((team) => team.team_slug === selectedTeamId);
        setTeamDetail(
          fallbackTeam
            ? {
                team: fallbackTeam,
                squad: [],
                keyPlayers: [],
                squadMeta: { players: 0, available: 0, estimated: 0 },
                startingLineup: { formation: "4-3-3", players: [] },
                ratingBreakdown: {},
              }
            : null,
        );
        setTeamError(fallbackTeam ? "" : "Could not load the selected team profile.");
      } finally {
        setTeamLoading(false);
      }
    }

    loadSelectedTeam();
  }, [selectedTeamId, teams]);

  async function handleRunSimulation() {
    setRunning(true);
    setError("");
    setMatchPreview(null);
    setSimulation(emptySimulation);
    setElapsedTime(null);
    const started = performance.now();
    try {
      const payload = await runSimulation({ iterations, injuries });
      setSimulation(payload);
      setElapsedTime(((performance.now() - started) / 1000).toFixed(2));
      setActiveTab("Predicted Bracket Path");
    } catch {
      setError("Simulation failed. Make sure the Flask backend is running.");
    } finally {
      setRunning(false);
    }
  }

  async function handleGenerateSquads() {
    setRunning(true);
    setError("");
    setSquadMessage("");
    try {
      const payload = await generateSquads();
      setError("");
      setSquadMessage(
        payload.fc26Available
          ? `Generated ${payload.generatedPlayers} players across ${payload.teams} teams.`
          : `FC26 dataset not found at ${payload.fc26Path}. Generated ${payload.generatedPlayers} estimated players across ${payload.teams} teams instead.`,
      );
      try {
        await refreshData(selectedTeamId);
        if (selectedTeamId) {
          const refreshed = await fetchTeam(selectedTeamId);
          setTeamDetail(refreshed);
        }
      } catch {
        setTeamError("");
      }
    } catch {
      setError("Squad generation failed.");
    } finally {
      setRunning(false);
    }
  }

  async function handleToggleInjury(playerName) {
    if (!teamDetail) {
      return;
    }
    const active = injuries.some(
      (entry) => entry.teamName === teamDetail.team.team_name && entry.playerName === playerName,
    );

    const nextInjuries = active
      ? injuries.filter(
          (entry) =>
            !(entry.teamName === teamDetail.team.team_name && entry.playerName === playerName),
        )
      : [
          ...injuries,
          {
            teamId: teamDetail.team.team_id,
            teamName: teamDetail.team.team_name,
            playerName,
          },
        ];

    setInjuries(nextInjuries);
    try {
      const payload = await previewInjury({
        teamId: teamDetail.team.team_id,
        injuries: nextInjuries,
        iterations: 1000,
      });
      setTeamDetail(payload.teamProfile);
      setSimulation(payload.simulation);
      setError("");
    } catch {
      setError("Could not recalculate the Injury Lab scenario.");
    }
  }

  async function handleMatchPreview() {
    if (teams.length < 2 || !selectedTeamId) {
      return;
    }
    const homeTeam = teams.find((team) => team.team_slug === selectedTeamId);
    if (!homeTeam) {
      return;
    }
    const challenger =
      teams.find((team) => team.group !== homeTeam?.group) ||
      teams.find((team) => team.team_slug !== selectedTeamId);
    if (!challenger) {
      return;
    }
    try {
      const payload = await simulateMatch({
        teamAId: homeTeam?.team_id,
        teamBId: challenger.team_id,
        injuries,
        knockout: true,
      });
      setMatchPreview(payload);
    } catch {
      setError("Could not generate the match preview.");
    }
  }

  const selectedProbabilities =
    simulation.probabilities.find((entry) => entry.team === teamDetail?.team?.team_name) || null;
  const bracketRounds = bracketByRound(simulation.sampleBracket);

  const topTen = simulation.probabilities.slice(0, 10);
  const hostCards = hostNations.map((nation) => ({ ...nation }));

  const teamXFactorMeta = teamDetail ? teamXFactorMap[teamDetail.team.team_name] || null : null;
  const teamXFactor = teamDetail
    ? findPlayerByName(teamDetail.squad, teamXFactorMeta?.player || "")
    : null;

  return (
    <main className="shell">
      <div className="experience-frame">
        <header className="masthead">
          <div className="brand-lockup">
            <div className="brand-mark">26</div>
            <div>
              <p className="eyebrow">World Cup Simulator</p>
              <h1>World Cup Simulator</h1>
            </div>
          </div>
          <div className="control-row">
            <div className="control-pill">
              <span>Simulation Count</span>
              <strong>{iterations.toLocaleString()}</strong>
            </div>
            <div className="option-row">
              {simulationOptions.map((option) => (
                <button
                  key={option.value}
                  className={iterations === option.value ? "option-pill active" : "option-pill"}
                  onClick={() => setIterations(option.value)}
                  disabled={running}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <button onClick={handleRunSimulation} disabled={running || loading}>
              {running ? "Simulating..." : "Run Simulation"}
            </button>
            <button className="ghost" onClick={handleGenerateSquads} disabled={running || loading}>
              Refresh Squads
            </button>
            <button className="ghost" onClick={handleMatchPreview} disabled={!teamDetail || running}>
              Match Preview
            </button>
          </div>
          {running ? (
            <div className="loading-panel">
              <div className="loading-bar" />
              <p>
                This can take a moment because the app is simulating thousands of full tournaments,
                including group stages, knockout paths, scorelines, and player goal outcomes.
              </p>
              <small>Use 250 or 1,000 simulations for a quicker preview while you iterate.</small>
            </div>
          ) : elapsedTime ? (
            <p className="timing-note">Last simulation completed in {elapsedTime}s.</p>
          ) : null}
        </header>

        <nav className="tab-row">
          {tabs.map((tab) => (
            <button
              key={tab}
              className={activeTab === tab ? "tab-pill active" : "tab-pill"}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </nav>

        {error ? <p className="error-banner">{error}</p> : null}
        {squadMessage ? <p className="success-banner">{squadMessage}</p> : null}

        {activeTab === "Overview" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>Host Nations</span>
                <span>tournament stage-setters</span>
              </div>
              <div className="host-grid">
                {hostCards.map((card) => (
                  <div className="host-card" key={card.team}>
                    <div className="host-flag">{card.flag}</div>
                    <h3>{card.team}</h3>
                    <p>Group {card.group}</p>
                  </div>
                ))}
              </div>
            </article>

            <section className="overview-grid">
              <article className="panel">
                <div className="panel-header">
                  <span>Top 10 Projected Teams</span>
                  <span>probabilities</span>
                </div>
                <div className="list">
                  {topTen.length ? (
                    topTen.map((entry) => {
                      const teamName = entry.team;
                      return (
                        <div className="list-row projected-card" key={teamName}>
                          <div className="row-with-media">
                            <div className="rank-badge">{simulation.probabilities.indexOf(entry) + 1}</div>
                            <PlayerVisual label={teamName} />
                            <div>
                              <strong>{teamName}</strong>
                            </div>
                          </div>
                          <div className="prob-columns">
                            <span>W {Math.round(entry.championProbability * 100)}%</span>
                            <span>F {Math.round(entry.finalProbability * 100)}%</span>
                            <span>SF {Math.round(entry.semiFinalProbability * 100)}%</span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="empty-state">Run a simulation to populate projected contenders.</p>
                  )}
                </div>
              </article>

              <article className="panel">
                <div className="panel-header">
                  <span>Host Cities & Locations</span>
                  <span>tournament footprint</span>
                </div>
                <div className="locations-grid">
                  {Object.entries(hostLocations).map(([country, locations]) => (
                    <div className="location-card" key={country}>
                      <h3>{country}</h3>
                      <div className="location-list">
                        {locations.map((location) => (
                          <span key={location}>{location}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <article className="panel">
              <div className="panel-header">
                <span>Match Preview</span>
                <span>single knockout sample</span>
              </div>
              {matchPreview ? (
                <div className="match-preview">
                  <div className="match-line">
                    <span>{matchPreview.homeTeam}</span>
                    <strong>{matchPreview.homeGoals}</strong>
                  </div>
                  <div className="match-line">
                    <span>{matchPreview.awayTeam}</span>
                    <strong>{matchPreview.awayGoals}</strong>
                  </div>
                  <p>Winner: {matchPreview.winner || "Level after regular time"}</p>
                  <p>Scorers: {matchPreview.scorers.join(", ") || "None"}</p>
                </div>
              ) : (
                <p className="empty-state">Use Match Preview to generate a one-off knockout scoreline.</p>
              )}
            </article>
          </section>
        ) : null}

        {activeTab === "Groups" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>Groups</span>
                <span>official layout</span>
              </div>
              {simulation.groups.length ? (
                <div className="group-table-grid">
                  {simulation.groups.map((group) => (
                    <div className="group-table-card" key={group.group}>
                      <h3>Group {group.group}</h3>
                      {group.table.map((row, index) => (
                        <div className="group-row" key={`${group.group}-${row.team}`}>
                          <span>
                            {index + 1}. {row.team}
                          </span>
                          <strong>{row.points} pts</strong>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="group-grid">
                  {groups.map((group) => (
                    <div className="group-card" key={group.group}>
                      <p>Group {group.group}</p>
                      {group.teams.map((team) => (
                        <strong key={team}>{team}</strong>
                      ))}
                    </div>
                  ))}
                </div>
              )}
            </article>
          </section>
        ) : null}

        {activeTab === "Team Lineup" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>Team Lineup</span>
                <select value={selectedTeamId} onChange={(event) => setSelectedTeamId(event.target.value)}>
                  {teams.map((team) => (
                    <option key={team.team_id} value={team.team_slug || teamSlug(team.team_name)}>
                      {team.team_name}
                    </option>
                  ))}
                </select>
              </div>

              {teamLoading ? <p className="empty-state">Loading selected team profile...</p> : null}
              {!teamLoading && teamError ? <p className="error-banner inline">{teamError}</p> : null}

              {!teamLoading && !teamError && teamDetail ? (
                <>
                  <div className="team-hero">
                    <PlayerVisual
                      player={teamXFactor}
                      label={teamDetail.team.team_name}
                      className="team-portrait"
                      fallbackClass="team-badge"
                    />
                    <div>
                      <h2>{teamDetail.team.team_name}</h2>
                      <p>
                        Group {teamDetail.team.group} · Projected strength{" "}
                        {Math.round(teamDetail.team.overall_strength * 100)}
                      </p>
                      <small>Fixed projected XI from the submitted lineup list.</small>
                    </div>
                  </div>

                  <div className="rating-grid">
                    {Object.entries(teamDetail.ratingBreakdown).map(([label, value]) => (
                      <div key={label} className="metric-card">
                        <span>{label.replace(/([A-Z])/g, " $1")}</span>
                        <strong>{Number(value).toFixed(2)}</strong>
                      </div>
                    ))}
                  </div>

                  <div className="subsection">
                    <div className="panel-header">
                      <span>Projected XI</span>
                      <span>{teamDetail.startingLineup?.formation || "4-3-3"}</span>
                    </div>
                    {teamDetail.startingLineup?.players?.length ? (
                      <div className="pitch">
                        <div className="pitch-lines" />
                        {lineupWithCoordinates(teamDetail.startingLineup).map((player) => (
                          <div
                            key={`${player.position}-${player.name}`}
                            className="pitch-player"
                            style={{ left: `${player.coordinate.x}%`, top: `${player.coordinate.y}%` }}
                          >
                            <PlayerVisual player={player} label={player.name} />
                            <div className="pitch-label">
                              <strong>
                                {player.name}
                                {player.captain ? <span className="captain-badge">C</span> : null}
                              </strong>
                              <small>{player.position}</small>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="empty-state">Projected lineup data is missing, so squad depth is shown below instead.</p>
                    )}
                  </div>

                  <div className="subsection">
                    <div className="panel-header">
                      <span>X-Factor</span>
                      <span>team driver</span>
                    </div>
                    <div className="x-factor-card">
                      <PlayerVisual player={teamXFactor} label={teamXFactorMeta?.label || teamDetail.team.team_name} />
                      <div>
                        <strong>{teamXFactorMeta?.label || "No tagged player yet."}</strong>
                        <p>
                          {selectedProbabilities
                            ? `Projected title probability: ${Math.round(selectedProbabilities.championProbability * 100)}%.`
                            : "Run a simulation to see how the x-factor changes the projected path."}
                        </p>
                        <small>{teamXFactorMeta?.reason || ""}</small>
                      </div>
                    </div>
                  </div>

                  <div className="subsection">
                    <div className="panel-header">
                      <span>Squad Preview</span>
                      <span>{teamDetail.squadMeta.players} players</span>
                    </div>
                    {teamDetail.squad.length ? (
                      <div className="list">
                        {teamDetail.squad.slice(0, 12).map((player) => {
                          const active = injuries.some(
                            (entry) =>
                              entry.teamName === teamDetail.team.team_name &&
                              entry.playerName === player.short_name,
                          );
                          return (
                            <div className="list-row" key={player.player_id}>
                              <div className="row-with-media">
                        <PlayerVisual player={player} label={player.short_name} />
                                <div>
                                  <strong>{player.short_name}</strong>
                                  <small>
                                    {player.position} · {player.club}
                                  </small>
                                </div>
                              </div>
                              <button
                                className={active ? "chip active" : "chip"}
                                onClick={() => handleToggleInjury(player.short_name)}
                              >
                                {active ? "Removed" : `OVR ${player.overall}`}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="empty-state">No squad data is available for this team yet.</p>
                    )}
                  </div>
                </>
              ) : null}
            </article>
          </section>
        ) : null}

        {activeTab === "Predicted Bracket Path" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>Predicted Bracket Path</span>
                <span>fresh sample every simulation</span>
              </div>
              {simulation.sampleBracket.length ? (
                <div className="bracket-rounds" key={simulation.simulationRunId || "empty-run"}>
                  {["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"].map((round) => (
                    <div className="round-column" key={round}>
                      <h3>{round}</h3>
                      {(bracketRounds[round] || []).map((match, index) => (
                        <div className="bracket-card" key={`${round}-${index}`}>
                          <p>{round}</p>
                          <div className="match-line">
                            <span>{match.homeTeam}</span>
                            <strong>{match.homeGoals}</strong>
                          </div>
                          <div className="match-line">
                            <span>{match.awayTeam}</span>
                            <strong>{match.awayGoals}</strong>
                          </div>
                          <span>Winner: {match.winner}</span>
                          {match.penalties ? <small>Note: wins on penalties</small> : null}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="empty-state">Run a simulation to generate a predicted bracket path.</p>
              )}
            </article>
          </section>
        ) : null}

        {activeTab === "X-Factors" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>X-Factors</span>
                <span>game-breakers and matchup tilters</span>
              </div>
              <div className="boot-grid">
                {xFactorCards.map(([team, playerName, position, reason]) => (
                  <div className="boot-card" key={`${team}-${playerName}`}>
                    <PlayerVisual label={playerName} player={{ player_name: playerName, short_name: playerName }} />
                    <div>
                      <strong>{playerName}</strong>
                      <p>
                        {team} · {position}
                      </p>
                      <span>{reason}</span>
                    </div>
                  </div>
                ))}
              </div>
            </article>

          </section>
        ) : null}
      </div>
    </main>
  );
}
