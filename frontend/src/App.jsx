import { useEffect, useState } from "react";
import {
  compareTeams,
  fetchGroups,
  fetchTeam,
  fetchTeams,
  generateSquads,
  previewInjury,
  runSimulation,
  simulateMatch,
} from "./api";
import { PLAYER_IMAGES } from "./playerImages";
import { X_FACTOR_RATINGS } from "./xFactorRatings";

const simulationOptions = [
  { label: "250", value: 250 },
  { label: "1,000", value: 1000 },
  { label: "5,000", value: 5000 },
  { label: "10,000 slower but more accurate", value: 10000 },
];

const emptySimulation = {
  probabilities: [],
  mostCommonScorelines: [],
  sampleBracket: [],
  topScorers: [],
  awards: null,
  groups: [],
  iterations: 1000,
  simulationRunId: null,
};

const tabs = [
  "Overview",
  "Groups",
  "Team Lineup",
  "Squad Comparison",
  "Predicted Bracket Path",
  "X-Factors",
];

const emptyComparison = {
  groupStage: null,
  knockoutStage: null,
  iterations: 0,
};

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

const COUNTRY_FLAGS = {
  Algeria: "/flags/algeria.png",
  Argentina: "/flags/argentina.png",
  Australia: "/flags/australia.png",
  Austria: "/flags/austria.png",
  Belgium: "/flags/belgium.png",
  "Bosnia and Herzegovina": "/flags/bosnia-and-herzegovina.png",
  Brazil: "/flags/brazil.png",
  Canada: "/flags/canada.png",
  "Cape Verde": "/flags/cape-verde.png",
  Colombia: "/flags/colombia.png",
  Croatia: "/flags/croatia.png",
  Curacao: "/flags/curacao.png",
  Czechia: "/flags/czechia.png",
  "DR Congo": "/flags/dr-congo.png",
  Ecuador: "/flags/ecuador.png",
  Egypt: "/flags/egypt.png",
  England: "/flags/england.png",
  France: "/flags/france.png",
  Germany: "/flags/germany.png",
  Ghana: "/flags/ghana.png",
  Haiti: "/flags/haiti.png",
  Iran: "/flags/iran.png",
  Iraq: "/flags/iraq.png",
  "Ivory Coast": "/flags/ivory-coast.png",
  Japan: "/flags/japan.png",
  Jordan: "/flags/jordan.png",
  "Korea Republic": "/flags/korea-republic.png",
  Mexico: "/flags/mexico.png",
  Morocco: "/flags/morocco.png",
  Netherlands: "/flags/netherlands.png",
  "New Zealand": "/flags/new-zealand.png",
  Norway: "/flags/norway.png",
  Panama: "/flags/panama.png",
  Paraguay: "/flags/paraguay.png",
  Portugal: "/flags/portugal.png",
  Qatar: "/flags/qatar.png",
  "Saudi Arabia": "/flags/saudi-arabia.png",
  Scotland: "/flags/scotland.png",
  Senegal: "/flags/senegal.png",
  "South Africa": "/flags/south-africa.png",
  Spain: "/flags/spain.png",
  Sweden: "/flags/sweden.png",
  Switzerland: "/flags/switzerland.png",
  Tunisia: "/flags/tunisia.png",
  Turkiye: "/flags/turkiye.png",
  "United States": "/flags/united-states.png",
  Uruguay: "/flags/uruguay.png",
  Uzbekistan: "/flags/uzbekistan.png",
};

const COUNTRY_COLORS = {
  Algeria: "#1f9d55",
  Argentina: "#7ec8f5",
  Australia: "#f0c22e",
  Austria: "#d62828",
  Belgium: "#d62828",
  "Bosnia and Herzegovina": "#2563eb",
  Brazil: "#f4c542",
  Canada: "#d62828",
  "Cape Verde": "#2563eb",
  Colombia: "#f4c542",
  "DR Congo": "#2563eb",
  Croatia: "#d62828",
  Curacao: "#2563eb",
  Czechia: "#d62828",
  Ecuador: "#f4c542",
  Egypt: "#d62828",
  England: "#f3f4f6",
  France: "#2563eb",
  Germany: "#f3f4f6",
  Ghana: "#f3f4f6",
  Haiti: "#2563eb",
  Iraq: "#1f9d55",
  Iran: "#f3f4f6",
  Japan: "#2563eb",
  Jordan: "#d62828",
  "Korea Republic": "#d62828",
  Mexico: "#1f9d55",
  Morocco: "#d62828",
  Netherlands: "#f97316",
  "New Zealand": "#f3f4f6",
  Norway: "#d62828",
  Panama: "#d62828",
  Paraguay: "#d62828",
  Portugal: "#d62828",
  Qatar: "#7a1533",
  "Saudi Arabia": "#1f9d55",
  Scotland: "#1e3a8a",
  Senegal: "#1f9d55",
  "South Africa": "#f4c542",
  Spain: "#d62828",
  Sweden: "#f4c542",
  Switzerland: "#d62828",
  Tunisia: "#d62828",
  Turkiye: "#d62828",
  "United States": "#1e3a8a",
  Uruguay: "#7ec8f5",
  Uzbekistan: "#2563eb",
  "Ivory Coast": "#f97316",
};

const xFactorPlayers = [
  { team: "France", player: "Kylian Mbappé", position: "Forward", reason: "Game-breaking pace and finishing make France's attack elite." },
  { team: "France", player: "Michael Olise", position: "Forward", reason: "Elite technical gravity and creative vision make him Europe's most dangerous dual-threat playmaker." },
  { team: "England", player: "Jude Bellingham", position: "Midfielder", reason: "Drives England through midfield with scoring and control." },
  { team: "England", player: "Harry Kane", position: "Forward", reason: "Elite finishing and link-up play give England a reliable goal source." },
  { team: "Spain", player: "Lamine Yamal", position: "Forward", reason: "A creative wide threat who can tilt tight knockout games." },
  { team: "Spain", player: "Pedri", position: "Midfielder", reason: "Controls tempo and chance creation for Spain." },
  { team: "Brazil", player: "Vinícius Júnior", position: "Forward", reason: "One of the best one-on-one attackers in the tournament." },
  { team: "Brazil", player: "Raphinha", position: "Forward", reason: "Elite vision and relentless energy on the flank." },
  { team: "Argentina", player: "Lionel Messi", position: "Forward", reason: "Still Argentina's main creator and late-game difference maker." },
  { team: "Argentina", player: "Julián Álvarez", position: "Forward", reason: "Pressing, movement, and finishing add depth to Argentina's attack." },
  { team: "Portugal", player: "Bruno Fernandes", position: "Midfielder", reason: "Portugal's creative engine and set-piece threat." },
  { team: "Portugal", player: "Cristiano Ronaldo", position: "Forward", reason: "Still a major box threat and finishing option." },
  { team: "Portugal", player: "Nuno Mendes", position: "Defender", reason: "Electric pace and elite technical quality make him the world's most complete wide threat." },
  { team: "Germany", player: "Florian Wirtz", position: "Midfielder", reason: "Creative force between the lines." },
  { team: "Germany", player: "Jamal Musiala", position: "Midfielder", reason: "Elite dribbling and chance creation." },
  { team: "Netherlands", player: "Virgil van Dijk", position: "Defender", reason: "Anchors one of the strongest defensive cores." },
  { team: "Morocco", player: "Achraf Hakimi", position: "Defender", reason: "Two-way fullback who drives Morocco's transition threat." },
  { team: "Norway", player: "Erling Haaland", position: "Forward", reason: "Elite penalty-box finishing keeps Norway dangerous in any draw." },
  { team: "Uruguay", player: "Federico Valverde", position: "Midfielder", reason: "Adds range, pressing, and late-box production." },
  { team: "Belgium", player: "Kevin De Bruyne", position: "Midfielder", reason: "Still the cleanest chance creator in Belgium's side." },
  { team: "Croatia", player: "Luka Modrić", position: "Midfielder", reason: "Still sets rhythm and solves pressure phases." },
  { team: "Senegal", player: "Sadio Mané", position: "Forward", reason: "Direct running and finishing can swing knockout ties." },
  { team: "Colombia", player: "Luis Díaz", position: "Forward", reason: "Direct dribbling and transition threat make him Colombia's sharpest edge." },
];

const teamBannerThemes = {
  Argentina: { abbr: "ARG", accent: "#6cc6ff", description: "Sky-blue striped texture with white glow lighting and a subtle Buenos Aires night-match atmosphere.", banner: "linear-gradient(135deg, #9edcff 0%, #e9f7ff 32%, #121821 32%, #0f1724 100%)" },
  Australia: { abbr: "AUS", accent: "#d7af3d", description: "Dark green and gold lighting with rugged stadium shadows and a desert-inspired texture wash.", banner: "linear-gradient(135deg, #103826 0%, #18563a 38%, #c59a2d 38%, #0d1217 100%)" },
  Austria: { abbr: "AUT", accent: "#d62839", description: "Sharp red and white minimalism with a cool alpine-inspired fog layer.", banner: "linear-gradient(135deg, #f7f7f7 0%, #ffffff 34%, #b91526 34%, #1b1f27 100%)" },
  Belgium: { abbr: "BEL", accent: "#e63946", description: "Black, red, and gold cinematic gradients with metallic lighting accents.", banner: "linear-gradient(135deg, #141414 0%, #141414 36%, #c11b2a 36%, #f3c33d 100%)" },
  Brazil: { abbr: "BRA", accent: "#f4d24c", description: "Yellow-green stadium glow with samba-inspired lighting and vivid pitch reflections.", banner: "linear-gradient(135deg, #0f582f 0%, #177846 36%, #f4d24c 36%, #0c2240 100%)" },
  Canada: { abbr: "CAN", accent: "#db2334", description: "A clean red-and-white stage with icy lighting and a subtle Toronto skyline atmosphere.", banner: "linear-gradient(135deg, #f5f7fb 0%, #ffffff 34%, #cf1d2d 34%, #95121d 100%)" },
  Colombia: { abbr: "COL", accent: "#f0c438", description: "Golden yellow and navy gradients with an energetic street-football pulse.", banner: "linear-gradient(135deg, #f0c438 0%, #e7b829 34%, #14284c 34%, #0f1722 100%)" },
  Croatia: { abbr: "CRO", accent: "#c41f2a", description: "Dark checkerboard texture with red-white lighting and dramatic shadows.", banner: "linear-gradient(135deg, #f5f7fb 0%, #f5f7fb 32%, #c41f2a 32%, #132649 100%)" },
  Denmark: { abbr: "DEN", accent: "#d62839", description: "Ultra-clean red and white Nordic minimalism with a subtle snowfall texture.", banner: "linear-gradient(135deg, #ffffff 0%, #f7f7f7 34%, #c51728 34%, #9d1320 100%)" },
  Ecuador: { abbr: "ECU", accent: "#efc33d", description: "Yellow and navy mountain-inspired lighting with dramatic altitude atmosphere.", banner: "linear-gradient(135deg, #efc33d 0%, #f4d454 34%, #193660 34%, #111924 100%)" },
  Egypt: { abbr: "EGY", accent: "#b3262f", description: "Deep red and black desert-night styling with geometric pyramid accents.", banner: "linear-gradient(135deg, #2a1116 0%, #4a1219 34%, #9f1d27 34%, #0d0f14 100%)" },
  England: { abbr: "ENG", accent: "#c72233", description: "White and red minimalism with Wembley-inspired floodlights and clean typography.", banner: "linear-gradient(135deg, #ffffff 0%, #f5f5f7 34%, #11161d 34%, #121822 100%)" },
  France: { abbr: "FRA", accent: "#3d74ff", description: "Dark blue gradients with subtle gold accents and Paris-night stadium lighting.", banner: "linear-gradient(135deg, #0e1530 0%, #13234f 34%, #d7bc6d 34%, #0d1016 100%)" },
  Germany: { abbr: "GER", accent: "#f4c36d", description: "Matte black and white styling with geometric lighting and a modern stadium glow.", banner: "linear-gradient(135deg, #0e0f12 0%, #151821 36%, #7b0d14 36%, #f4c36d 100%)" },
  Ghana: { abbr: "GHA", accent: "#f1c44a", description: "Rich red, yellow, and green textures with warm crowd-lit stadium energy.", banner: "linear-gradient(135deg, #5e1119 0%, #7f1b23 34%, #e4b53d 34%, #1f5a34 100%)" },
  Iran: { abbr: "IRN", accent: "#1ea66b", description: "Emerald green and white gradients with Persian-inspired geometric textures.", banner: "linear-gradient(135deg, #114032 0%, #1b5e49 36%, #edf3f6 36%, #a81f2c 100%)" },
  Iraq: { abbr: "IRQ", accent: "#238754", description: "Dark green and black atmosphere with bold national highlights and heavy stadium fog.", banner: "linear-gradient(135deg, #0e1713 0%, #13211a 36%, #1d6b43 36%, #0c1015 100%)" },
  Italy: { abbr: "ITA", accent: "#3e72ff", description: "Royal blue and silver cinematic styling with elegant Roman-inspired texture cues.", banner: "linear-gradient(135deg, #1d2f60 0%, #2a4485 36%, #c9d3e8 36%, #11161d 100%)" },
  Japan: { abbr: "JPN", accent: "#e73a48", description: "Ultra-clean white and navy minimalism with subtle Tokyo neon accents.", banner: "linear-gradient(135deg, #f5f7fb 0%, #ffffff 34%, #14243b 34%, #e73a48 100%)" },
  Mexico: { abbr: "MEX", accent: "#24a162", description: "Dark green and red gradients with Aztec-inspired geometric overlays and vibrant floodlights.", banner: "linear-gradient(135deg, #0f3e29 0%, #17573b 36%, #c81f34 36%, #10161d 100%)" },
  Morocco: { abbr: "MAR", accent: "#bf2237", description: "Deep red with geometric Moroccan patterns and warm golden night lighting.", banner: "linear-gradient(135deg, #4b0d18 0%, #7a1327 36%, #c59155 36%, #19120f 100%)" },
  Netherlands: { abbr: "NED", accent: "#ff8a2a", description: "Bright orange glow with black contrast accents and an Amsterdam-night atmosphere.", banner: "linear-gradient(135deg, #18263a 0%, #22334a 36%, #ff8a2a 36%, #f2f5fb 100%)" },
  "New Zealand": { abbr: "NZL", accent: "#d5dae6", description: "Black and silver minimalism with stormy cinematic lighting.", banner: "linear-gradient(135deg, #101317 0%, #181d24 36%, #7d8797 36%, #d8dde6 100%)" },
  Nigeria: { abbr: "NGA", accent: "#2ad36b", description: "Neon green and black energy with street-football inspired textures.", banner: "linear-gradient(135deg, #0c1210 0%, #111a14 36%, #1cb45a 36%, #0e1013 100%)" },
  Norway: { abbr: "NOR", accent: "#cf3948", description: "Icy blue and red Nordic lighting with a cold stadium atmosphere.", banner: "linear-gradient(135deg, #cde8ff 0%, #eff7ff 34%, #24467e 34%, #bf2438 100%)" },
  Paraguay: { abbr: "PAR", accent: "#cc3343", description: "Dark red and blue gradients with classic South American football energy.", banner: "linear-gradient(135deg, #1f3161 0%, #274179 34%, #b91f33 34%, #121821 100%)" },
  Poland: { abbr: "POL", accent: "#d12538", description: "Sharp white-red contrast with cold stadium lighting.", banner: "linear-gradient(135deg, #f7f8fb 0%, #ffffff 34%, #d12538 34%, #941727 100%)" },
  Portugal: { abbr: "POR", accent: "#27a15d", description: "Dark red and green lighting with an elegant Lisbon-night cinematic atmosphere.", banner: "linear-gradient(135deg, #500c16 0%, #6d1220 38%, #1f7f4d 38%, #10161d 100%)" },
  Qatar: { abbr: "QAT", accent: "#d3ab5f", description: "Maroon and gold luxury-inspired lighting with a desert-night atmosphere.", banner: "linear-gradient(135deg, #4a0f28 0%, #611438 36%, #cda558 36%, #171114 100%)" },
  "Saudi Arabia": { abbr: "KSA", accent: "#22a56e", description: "Emerald green with gold accents and desert-inspired floodlight haze.", banner: "linear-gradient(135deg, #103f2c 0%, #176146 36%, #cfb36c 36%, #11161c 100%)" },
  Senegal: { abbr: "SEN", accent: "#e4ba3f", description: "Deep green, yellow, and red gradients with vibrant crowd-inspired energy.", banner: "linear-gradient(135deg, #114028 0%, #1a5e39 34%, #d4aa37 34%, #a61f2f 100%)" },
  Serbia: { abbr: "SRB", accent: "#cf2f45", description: "Dark red and navy aggression with Balkan-inspired stadium intensity.", banner: "linear-gradient(135deg, #18264b 0%, #203661 34%, #a41a2c 34%, #0f141b 100%)" },
  "South Africa": { abbr: "RSA", accent: "#f0c241", description: "A vibrant multicolor glow with energetic Johannesburg football-culture textures.", banner: "linear-gradient(135deg, #11623d 0%, #188755 28%, #d2a531 28%, #ab1e2e 64%, #203a75 100%)" },
  "South Korea": { abbr: "KOR", accent: "#d92e42", description: "White and red futuristic Seoul-inspired neon styling.", banner: "linear-gradient(135deg, #f8fafc 0%, #ffffff 34%, #d92e42 34%, #16253d 100%)" },
  Spain: { abbr: "ESP", accent: "#f2c14d", description: "Deep red and gold royal styling with warm cinematic lighting and subtle texture layering.", banner: "linear-gradient(135deg, #6e1018 0%, #8c1520 36%, #f2c14d 36%, #1a2140 100%)" },
  Switzerland: { abbr: "SUI", accent: "#d62839", description: "Red-and-white luxury minimalism with alpine lighting atmosphere.", banner: "linear-gradient(135deg, #b81424 0%, #d62839 36%, #ffffff 36%, #edf1f7 100%)" },
  Tunisia: { abbr: "TUN", accent: "#cf2535", description: "Dark red and white stadium glow with North African geometric accents.", banner: "linear-gradient(135deg, #4d1119 0%, #761926 36%, #ffffff 36%, #11161d 100%)" },
  Turkiye: { abbr: "TUR", accent: "#d9273d", description: "Crimson-red cinematic atmosphere with dramatic night lighting.", banner: "linear-gradient(135deg, #611019 0%, #8a1723 36%, #d9273d 36%, #0f141b 100%)" },
  "United States": { abbr: "USA", accent: "#325dce", description: "Navy-red broadcast lighting with metallic textures and a modern stadium edge.", banner: "linear-gradient(135deg, #13274b 0%, #1d4178 36%, #c6374a 36%, #f2f4f8 100%)" },
  Uruguay: { abbr: "URU", accent: "#77c9ff", description: "Sky blue and black football-heritage styling with a Montevideo night-match feel.", banner: "linear-gradient(135deg, #bde7ff 0%, #eff8ff 34%, #1b2737 34%, #0f141b 100%)" },
  Wales: { abbr: "WAL", accent: "#d22d41", description: "Deep red dragon-inspired atmosphere with smoky cinematic lighting.", banner: "linear-gradient(135deg, #58121c 0%, #7f1b29 36%, #d22d41 36%, #12161d 100%)" },
};

const attributeOrder = [
  ["pace", "PAC"],
  ["shooting", "SHO"],
  ["passing", "PAS"],
  ["dribbling", "DRI"],
  ["defending", "DEF"],
  ["physic", "PHY"],
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

function countryFlagPath(teamName) {
  return COUNTRY_FLAGS[teamName] || null;
}

function resolveCountryName(teamName) {
  const aliasMap = {
    "IR Iran": "Iran",
    "USA": "United States",
    "Cabo Verde": "Cape Verde",
    "Côte d'Ivoire": "Ivory Coast",
  };
  return aliasMap[teamName] || teamName;
}

function countryColor(teamName) {
  return COUNTRY_COLORS[resolveCountryName(teamName)] || themeForTeam(teamName).accent;
}

function displayCountryColor(teamName) {
  const color = countryColor(teamName);
  const normalized = color.replace("#", "").toLowerCase();
  if (normalized === "f3f4f6" || normalized === "ffffff" || normalized === "f5f5f5") {
    return "#6b7280";
  }
  return color;
}

function hexToRgba(hex, alpha) {
  const normalized = (hex || "").replace("#", "");
  if (normalized.length !== 6) {
    return `rgba(61, 116, 255, ${alpha})`;
  }
  const red = parseInt(normalized.slice(0, 2), 16);
  const green = parseInt(normalized.slice(2, 4), 16);
  const blue = parseInt(normalized.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
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

function groupAverageRanking(group, teams) {
  if (!group?.teams?.length || !teams?.length) {
    return null;
  }

  const lookup = new Map(teams.map((team) => [team.team_name, team]));
  const ranks = group.teams
    .map((teamName) => Number(lookup.get(teamName)?.fifa_rank))
    .filter((value) => Number.isFinite(value));

  if (!ranks.length) {
    return null;
  }

  return Math.round((ranks.reduce((sum, value) => sum + value, 0) / ranks.length) * 10) / 10;
}

function formatAverageRanking(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "--";
  }
  return numeric % 1 === 0 ? `${numeric}` : numeric.toFixed(1);
}

function themeForTeam(teamName) {
  const aliasMap = {
    "Korea Republic": "South Korea",
    Türkiye: "Turkiye",
  };
  const resolvedName = aliasMap[teamName] || teamName;
  return (
    teamBannerThemes[resolvedName] || {
      abbr: initials(resolvedName),
      accent: "#3d74ff",
      description: "A cinematic pre-match treatment with national color accents and broadcast-style lighting.",
      banner: "linear-gradient(135deg, #11161d 0%, #1e2732 42%, #e9eef7 42%, #ffffff 100%)",
    }
  );
}

function statValue(player, key) {
  const value = Number(player?.[key]);
  return Number.isFinite(value) ? Math.round(value) : null;
}

function ratingValue(player, fallback = null) {
  const value = Number(player?.overall);
  return Number.isFinite(value) ? Math.round(value) : fallback;
}

function formatMetricValue(value, whole = false) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "--";
  }
  return whole ? `${Math.round(numeric)}` : numeric.toFixed(2);
}

function probabilityPercent(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "--";
  }
  return `${Math.round(numeric * 100)}%`;
}

function normalizedPercentages(values) {
  const numericValues = values.map((value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? Math.max(0, numeric) : 0;
  });
  const total = numericValues.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return numericValues.map(() => "--");
  }

  const scaled = numericValues.map((value) => (value / total) * 100);
  const base = scaled.map((value) => Math.floor(value));
  let remainder = 100 - base.reduce((sum, value) => sum + value, 0);

  const order = scaled
    .map((value, index) => ({ index, fraction: value - Math.floor(value) }))
    .sort((left, right) => right.fraction - left.fraction);

  for (let index = 0; index < order.length && remainder > 0; index += 1) {
    base[order[index].index] += 1;
    remainder -= 1;
  }

  return base.map((value) => `${value}%`);
}

function positionLabel(player, fallback = "Starter") {
  return player?.position || fallback;
}

function resolvePlayerRecord(pool, playerName) {
  return findPlayerByName(pool, playerName) || { name: playerName, short_name: playerName, player_name: playerName };
}

function applyXFactorRatings(playerLike, playerName) {
  const override =
    X_FACTOR_RATINGS[playerName] ||
    X_FACTOR_RATINGS[playerLike?.player] ||
    X_FACTOR_RATINGS[playerLike?.name] ||
    X_FACTOR_RATINGS[playerLike?.short_name] ||
    X_FACTOR_RATINGS[playerLike?.long_name];

  if (!override) {
    return playerLike;
  }

  return {
    ...playerLike,
    ...override,
  };
}

function teamXFactors(teamName, squad = [], startingLineup = { players: [] }) {
  const pool = [...(startingLineup?.players || []), ...(squad || [])];
  return xFactorPlayers
    .filter((entry) => entry.team === teamName)
    .map((entry) =>
      applyXFactorRatings(
        {
          ...resolvePlayerRecord(pool, entry.player),
          team: entry.team,
          player: entry.player,
          reason: entry.reason,
          position: entry.position,
          country: entry.team,
        },
        entry.player,
      ),
    );
}

function FootballCard({ player, teamName, reason, compact = false }) {
  const theme = themeForTeam(teamName);
  const label = player?.player || player?.name || player?.short_name || "Unknown";
  const overall = ratingValue(player, null);
  return (
    <article
      className={compact ? "football-card football-card-compact" : "football-card"}
      style={{ "--team-accent": theme.accent, "--team-banner": theme.banner }}
    >
      <div className="football-card-top">
        <div>
          <strong className="football-card-rating">{overall ?? "--"}</strong>
          <span className="football-card-position">{positionLabel(player, player?.position || "XF")}</span>
        </div>
        <TeamFlag
          teamName={player?.country || teamName}
          className="football-card-country football-card-flag"
          fallbackClass="football-card-country"
          alt={`${player?.country || teamName} flag`}
        />
      </div>
      <div className="football-card-avatar-wrap">
        <PlayerVisual
          player={player}
          label={label}
          className={compact ? "football-card-avatar football-card-avatar-compact" : "football-card-avatar"}
          fallbackClass={compact ? "football-card-fallback football-card-fallback-compact" : "football-card-fallback"}
        />
      </div>
      <div className="football-card-body">
        <strong className="football-card-name">{label}</strong>
        <p className="football-card-meta">
          {teamName} · {positionLabel(player, player?.position || "Impact player")}
        </p>
        {reason ? <p className="football-card-reason">{reason}</p> : null}
      </div>
      {!compact ? (
        <div className="football-card-stats">
          {attributeOrder.map(([key, labelText]) => (
            <div className="football-stat" key={`${label}-${key}`}>
              <span>{labelText}</span>
              <strong>{statValue(player, key) ?? "--"}</strong>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function LineupPlayerTile({ player, teamName }) {
  const theme = themeForTeam(teamName);
  const label = player?.name || player?.short_name || "Starter";
  return (
    <div className="lineup-tile" style={{ "--team-accent": theme.accent }}>
      <div className="lineup-tile-top">
        <span className="lineup-tile-rating">{ratingValue(player, null) ?? "--"}</span>
        <span className="lineup-tile-pos">{positionLabel(player)}</span>
      </div>
      <div className="lineup-tile-fallback">{initials(label)}</div>
      <div className="lineup-tile-name">
        <strong>{label}</strong>
        {player?.captain ? <span className="captain-badge">C</span> : null}
      </div>
    </div>
  );
}

function InitialsVisual({ label, className = "avatar-fallback" }) {
  return <div className={className}>{initials(label)}</div>;
}

function TeamFlag({
  teamName,
  className = "team-flag",
  fallbackClass = "team-flag team-flag-fallback",
  alt,
}) {
  const src = countryFlagPath(teamName);
  if (src) {
    return <img className={className} src={src} alt={alt || `${teamName} flag`} />;
  }
  return <div className={fallbackClass}>{initials(teamName)}</div>;
}

const formationSlots = {
  "4-3-3": [
    { role: ["GK"], x: 50, y: 90 },
    { role: ["RB", "RWB"], x: 79, y: 72 },
    { role: ["RCB", "CB"], x: 61, y: 68 },
    { role: ["LCB", "CB"], x: 39, y: 68 },
    { role: ["LB", "LWB"], x: 21, y: 72 },
    { role: ["CDM"], x: 50, y: 57 },
    { role: ["LCM", "CM", "LM"], x: 34, y: 46 },
    { role: ["RCM", "CM", "RM"], x: 66, y: 46 },
    { role: ["RW"], x: 82, y: 18 },
    { role: ["ST", "CF"], x: 50, y: 10 },
    { role: ["LW"], x: 18, y: 18 }
  ],
  "4-4-2": [
    { role: ["GK"], x: 50, y: 88 },
    { role: ["RB", "RWB"], x: 78, y: 70 },
    { role: ["RCB", "CB"], x: 60, y: 66 },
    { role: ["LCB", "CB"], x: 40, y: 66 },
    { role: ["LB", "LWB"], x: 22, y: 70 },
    { role: ["RM", "RW"], x: 80, y: 48 },
    { role: ["RCM", "CM", "CDM"], x: 58, y: 50 },
    { role: ["LCM", "CM", "CDM"], x: 42, y: 50 },
    { role: ["LM", "LW"], x: 20, y: 48 },
    { role: ["RS", "ST", "CF"], x: 40, y: 20 },
    { role: ["LS", "ST", "CF"], x: 60, y: 20 }
  ],
  "4-2-3-1": [
    { role: ["GK"], x: 50, y: 90 },
    { role: ["RB", "RWB"], x: 79, y: 72 },
    { role: ["RCB", "CB"], x: 61, y: 72 },
    { role: ["LCB", "CB"], x: 39, y: 72 },
    { role: ["LB", "LWB"], x: 21, y: 72 },
    { role: ["RCDM", "CDM", "CM"], x: 58, y: 49 },
    { role: ["LCDM", "CDM", "CM"], x: 42, y: 49 },
    { role: ["RW", "RM"], x: 81, y: 30 },
    { role: ["CAM", "CF"], x: 50, y: 27 },
    { role: ["LW", "LM"], x: 19, y: 30 },
    { role: ["ST", "CF"], x: 50, y: 6 }
  ],
  "3-4-2-1": [
    { role: ["GK"], x: 50, y: 90 },
    { role: ["RCB", "CB"], x: 68, y: 73 },
    { role: ["CB"], x: 50, y: 69 },
    { role: ["LCB", "CB"], x: 32, y: 73 },
    { role: ["RM", "RWB"], x: 80, y: 53 },
    { role: ["RCM", "CM", "CDM"], x: 58, y: 54 },
    { role: ["LCM", "CM", "CDM"], x: 42, y: 54 },
    { role: ["LM", "LWB"], x: 20, y: 53 },
    { role: ["RCAM", "CAM", "CF"], x: 61, y: 33 },
    { role: ["LCAM", "CAM", "CF"], x: 39, y: 33 },
    { role: ["ST", "CF"], x: 50, y: 8 }
  ],
  "3-4-3": [
    { role: ["GK"], x: 50, y: 90 },
    { role: ["RCB", "CB"], x: 68, y: 73 },
    { role: ["CB"], x: 50, y: 69 },
    { role: ["LCB", "CB"], x: 32, y: 73 },
    { role: ["RM", "RWB"], x: 80, y: 53 },
    { role: ["RCM", "CM", "CDM"], x: 58, y: 54 },
    { role: ["LCM", "CM", "CDM"], x: 42, y: 54 },
    { role: ["LM", "LWB"], x: 20, y: 53 },
    { role: ["RW"], x: 82, y: 18 },
    { role: ["ST", "CF"], x: 50, y: 10 },
    { role: ["LW"], x: 18, y: 18 }
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
  const targetTokens = slugifyName(candidate).split("-").filter(Boolean);
  let bestMatch = null;
  let bestScore = 0;

  for (const player of players) {
    const values = [player.name, player.short_name, player.long_name, player.player_name].filter(Boolean);
    for (const value of values) {
      const normalized = normalizeName(value);
      if (!normalized) {
        continue;
      }
      if (normalized === target) {
        return player;
      }
      let score = 0;
      if (target && (normalized.includes(target) || target.includes(normalized))) {
        score = 0.92;
      } else {
        const valueTokens = slugifyName(value).split("-").filter(Boolean);
        const overlap = targetTokens.filter((token) => valueTokens.includes(token)).length;
        if (overlap) {
          score = overlap / Math.max(targetTokens.length, 1);
        }
      }
      if (score > bestScore) {
        bestScore = score;
        bestMatch = player;
      }
    }
  }

  return bestScore >= 0.5 ? bestMatch : null;
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

function canonicalPosition(position) {
  const value = String(position || "CM").toUpperCase();
  if (["GK","RB","RCB","CB","LCB","LB","RWB","LWB","CDM","CM","CAM","RM","LM","RW","LW","ST","CF"].includes(value)) {
    return value;
  }
  return value;
}

function positionFallbacks(position) {
  const map = {
    GK: ["GK"],
    RB: ["RB", "RWB", "RCB"],
    RCB: ["RCB", "CB", "RB"],
    CB: ["CB", "RCB", "LCB"],
    LCB: ["LCB", "CB", "LB"],
    LB: ["LB", "LWB", "LCB"],
    RWB: ["RWB", "RB", "RM"],
    LWB: ["LWB", "LB", "LM"],
    CDM: ["CDM", "CM"],
    CM: ["CM", "CDM", "CAM"],
    CAM: ["CAM", "CM", "CF"],
    RM: ["RM", "RW", "RWB", "CM"],
    LM: ["LM", "LW", "LWB", "CM"],
    RW: ["RW", "RM", "CF"],
    LW: ["LW", "LM", "CF"],
    ST: ["ST", "CF", "CAM"],
    CF: ["CF", "ST", "CAM"],
  };
  return map[canonicalPosition(position)] || [canonicalPosition(position)];
}

function scorePlayerForSlot(player, slotRoles) {
  const fallbacks = positionFallbacks(player?.position);
  for (let index = 0; index < fallbacks.length; index += 1) {
    if (slotRoles.includes(fallbacks[index])) {
      return 100 - index * 10;
    }
  }
  return -1;
}

function lineupWithCoordinates(startingLineup) {
  const players = [...(startingLineup?.players || [])];
  const slots = formationSlots[startingLineup?.formation] || formationSlots["4-3-3"];
  const assigned = new Array(players.length).fill(false);

  const positioned = slots.map((slot) => {
    let bestIndex = -1;
    let bestScore = -1;

    players.forEach((player, index) => {
      if (assigned[index]) {
        return;
      }
      const score = scorePlayerForSlot(player, slot.role);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });

    if (bestIndex === -1) {
      bestIndex = assigned.findIndex((taken) => !taken);
    }

    if (bestIndex === -1) {
      return null;
    }

    assigned[bestIndex] = true;
    return {
      ...players[bestIndex],
      coordinate: { x: slot.x, y: slot.y },
    };
  }).filter(Boolean);

  const leftovers = players
    .map((player, index) => ({ player, index }))
    .filter(({ index }) => !assigned[index])
    .map(({ player }) => ({
      ...player,
      coordinate: { x: 50, y: 50 },
    }));

  return [...positioned, ...leftovers];
}

function normalizeTeamPayload(payload) {
  return {
    ...payload,
    squad: payload?.squad || [],
    keyPlayers: payload?.keyPlayers || [],
    squadMeta: payload?.squadMeta || { players: 0, available: 0, estimated: 0 },
    startingLineup: payload?.startingLineup || { formation: "4-3-3", players: [] },
    ratingBreakdown: payload?.ratingBreakdown || {},
  };
}

function awardSubtitle(entry) {
  if (!entry) {
    return null;
  }
  const teamLabel = entry.team || entry.country || "";
  if (entry.goals != null) {
    return teamLabel ? `${teamLabel} · ${entry.goals} goals` : `${entry.goals} goals`;
  }
  return teamLabel ? `${teamLabel} · ${entry.position}` : `${entry.position}`;
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
  const [comparison, setComparison] = useState(emptyComparison);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");
  const [comparisonMode, setComparisonMode] = useState("knockout");
  const [compareTeamAId, setCompareTeamAId] = useState("");
  const [compareTeamBId, setCompareTeamBId] = useState("");
  const [compareTeamADetail, setCompareTeamADetail] = useState(null);
  const [compareTeamBDetail, setCompareTeamBDetail] = useState(null);
  const [meta, setMeta] = useState(null);
  const [xFactorProfiles, setXFactorProfiles] = useState({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [squadMessage, setSquadMessage] = useState("");
  const [elapsedTime, setElapsedTime] = useState(null);

  async function loadSelectedTeamProfile(teamId, currentTeams, options = {}) {
    const { preserveExisting = false } = options;
    if (!teamId) {
      setTeamDetail(null);
      return;
    }
    if (!preserveExisting) {
      setTeamLoading(true);
    }
    setTeamError("");
    try {
      const payload = await fetchTeam(teamId);
      setTeamDetail(normalizeTeamPayload(payload));
    } catch {
      const fallbackTeam = currentTeams.find((team) => team.team_slug === teamId);
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
      if (!preserveExisting) {
        setTeamLoading(false);
      }
    }
  }

  async function refreshData(keepTeamId) {
    const [groupsPayload, teamsPayload] = await Promise.all([fetchGroups(), fetchTeams()]);
    setGroups(groupsPayload.groups || []);
    setTeams(teamsPayload.teams || []);
    setMeta(teamsPayload.meta || null);
    if (!compareTeamAId) {
      setCompareTeamAId(teamsPayload.teams[0]?.team_slug || "");
    }
    if (!compareTeamBId) {
      setCompareTeamBId(
        teamsPayload.teams.find((team) => team.team_slug !== (teamsPayload.teams[0]?.team_slug || ""))?.team_slug || "",
      );
    }
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
    loadSelectedTeamProfile(selectedTeamId, teams);
  }, [selectedTeamId, teams]);

  useEffect(() => {
    async function loadComparisonProfiles() {
      if (!teams.length || !compareTeamAId || !compareTeamBId) {
        return;
      }
      try {
        const [teamA, teamB] = await Promise.all([fetchTeam(compareTeamAId), fetchTeam(compareTeamBId)]);
        setCompareTeamADetail(normalizeTeamPayload(teamA));
        setCompareTeamBDetail(normalizeTeamPayload(teamB));
      } catch {
        setComparisonError("Could not load the comparison teams.");
      }
    }

    loadComparisonProfiles();
  }, [teams, compareTeamAId, compareTeamBId]);

  useEffect(() => {
    if (!teams.length) {
      return undefined;
    }

    let cancelled = false;

    async function loadXFactorProfiles() {
      const uniqueTeams = [...new Set(xFactorPlayers.map((entry) => entry.team))];
      const payloads = await Promise.all(
        uniqueTeams.map(async (teamName) => {
          const match = teams.find((team) => team.team_name === teamName);
          if (!match) {
            return null;
          }
          try {
            return [teamName, await fetchTeam(match.team_slug || teamSlug(teamName))];
          } catch {
            return null;
          }
        }),
      );
      if (!cancelled) {
        setXFactorProfiles(
          Object.fromEntries(
            payloads
              .filter(Boolean)
              .map(([teamName, payload]) => [teamName, normalizeTeamPayload(payload)]),
          ),
        );
      }
    }

    loadXFactorProfiles();
    return () => {
      cancelled = true;
    };
  }, [teams]);

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
          setTeamDetail(normalizeTeamPayload(refreshed));
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

  async function handleResetSimulation() {
    setRunning(true);
    setError("");
    setSquadMessage("");
    setElapsedTime(null);
    setSimulation(emptySimulation);
    setComparison(emptyComparison);
    setComparisonError("");
    setMatchPreview(null);
    setInjuries([]);
    setActiveTab("Overview");
    try {
      await Promise.all([
        selectedTeamId
          ? loadSelectedTeamProfile(selectedTeamId, teams, { preserveExisting: true })
          : Promise.resolve(),
        compareTeamAId
          ? fetchTeam(compareTeamAId).then((payload) =>
              setCompareTeamADetail(normalizeTeamPayload(payload)),
            )
          : Promise.resolve(),
        compareTeamBId
          ? fetchTeam(compareTeamBId).then((payload) =>
              setCompareTeamBDetail(normalizeTeamPayload(payload)),
            )
          : Promise.resolve(),
      ]);
    } catch {
      setError("Could not reset the current simulation state.");
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
      setTeamDetail(normalizeTeamPayload(payload.teamProfile));
      setSimulation(payload.simulation);
      setError("");
    } catch {
      setError("Could not recalculate the Injury Lab scenario.");
    }
  }

  async function handleMatchPreview() {
    setActiveTab("Squad Comparison");
  }

  async function handleRunComparison() {
    if (!compareTeamAId || !compareTeamBId || compareTeamAId === compareTeamBId) {
      setComparisonError("Choose two different teams to compare.");
      return;
    }

    const teamA = teams.find((team) => team.team_slug === compareTeamAId);
    const teamB = teams.find((team) => team.team_slug === compareTeamBId);
    if (!teamA || !teamB) {
      setComparisonError("Could not resolve the selected teams.");
      return;
    }

    setComparisonLoading(true);
    setComparisonError("");
    try {
      const payload = await compareTeams({
        teamAId: teamA.team_id,
        teamBId: teamB.team_id,
        injuries,
        iterations: Math.min(iterations, 5000),
      });
      setComparison(payload);
    } catch {
      setComparisonError("Could not generate the squad comparison.");
    } finally {
      setComparisonLoading(false);
    }
  }

  const selectedProbabilities =
    simulation.probabilities.find((entry) => entry.team === teamDetail?.team?.team_name) || null;
  const bracketRounds = bracketByRound(simulation.sampleBracket);

  const topTen = simulation.probabilities.slice(0, 10);
  const awards = simulation.awards || null;
  const awardEntries = awards
    ? [
        ["Golden Ball", awards.goldenBall],
        ["Silver Ball", awards.silverBall],
        ["Bronze Ball", awards.bronzeBall],
        ["Golden Boot", awards.goldenBoot],
        ["Silver Boot", awards.silverBoot],
        ["Bronze Boot", awards.bronzeBoot],
        ["Golden Glove", awards.goldenGlove],
        ["Best Young Player", awards.bestYoungPlayer],
      ]
    : [];
  const hostCards = hostNations.map((nation) => ({ ...nation }));
  const hostLocationTicker = Object.entries(hostLocations).map(([country, locations]) => ({
    country,
    locations,
    color: countryColor(country),
  }));
  const lineupPlayers = lineupWithCoordinates(teamDetail?.startingLineup);
  const currentTeamTheme = themeForTeam(teamDetail?.team?.team_name || "");
  const teamXFactorList = teamDetail
    ? teamXFactors(teamDetail.team.team_name, teamDetail.squad, teamDetail.startingLineup)
    : [];
  const xFactorShowcase = xFactorPlayers.map((entry) => {
    const profile = xFactorProfiles[entry.team];
    const pool = profile ? [...(profile.startingLineup?.players || []), ...(profile.squad || [])] : [];
    return applyXFactorRatings(
      {
        ...resolvePlayerRecord(pool, entry.player),
        team: entry.team,
        player: entry.player,
        reason: entry.reason,
        position: entry.position,
        country: entry.team,
      },
      entry.player,
    );
  });
  const comparisonTeamAXFactors = compareTeamADetail
    ? teamXFactors(compareTeamADetail.team.team_name, compareTeamADetail.squad, compareTeamADetail.startingLineup)
    : [];
  const comparisonTeamBXFactors = compareTeamBDetail
    ? teamXFactors(compareTeamBDetail.team.team_name, compareTeamBDetail.squad, compareTeamBDetail.startingLineup)
    : [];
  const comparisonActive =
    comparisonMode === "group" ? comparison.groupStage : comparison.knockoutStage;
  const comparisonPercentages =
    comparisonMode === "group"
      ? normalizedPercentages([
          comparison.groupStage?.teamAWinProbability,
          comparison.groupStage?.drawProbability,
          comparison.groupStage?.teamBWinProbability,
        ])
      : normalizedPercentages([
          comparison.knockoutStage?.teamAWinProbability,
          comparison.knockoutStage?.teamBWinProbability,
        ]);

  return (
    <main className="shell">
      <div className="experience-frame">
        <header className="masthead">
          <div className="brand-lockup">
            <div className="brand-mark">
              <img src="/branding/world-cup-2026-logo.webp" alt="FIFA World Cup 2026 logo" />
            </div>
            <div>
              <p className="eyebrow">Monte Carlo Simulation</p>
              <h1>World Cup 2026 Simulation</h1>
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
            <button className="run-button" onClick={handleRunSimulation} disabled={running || loading}>
              {running ? "Simulating..." : "Run Simulation"}
            </button>
            <button className="reset-button" onClick={handleResetSimulation} disabled={running || loading}>
              Reset Simulation
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
                    <TeamFlag
                      teamName={card.team}
                      className="host-flag host-flag-image"
                      fallbackClass="host-flag"
                      alt={`${card.team} flag`}
                    />
                    <h3>{card.team}</h3>
                    <p>Group {card.group}</p>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel">
              <div className="panel-header">
                <span>Host Cities & Locations</span>
                <span>tournament footprint</span>
              </div>
              <div className="ticker-shell">
                <div className="ticker-fade ticker-fade-left" />
                <div className="ticker-fade ticker-fade-right" />
                <div className="ticker-window">
                  <div className="ticker-track">
                    {[...hostLocationTicker, ...hostLocationTicker].map((entry, index) => (
                      <div
                        className="ticker-segment"
                        key={`${entry.country}-${index}`}
                        style={{
                          "--ticker-accent": displayCountryColor(entry.country),
                          "--ticker-soft": hexToRgba(entry.color, 0.14),
                        }}
                      >
                        <span className="ticker-country">{entry.country}</span>
                        <div className="ticker-chips">
                          {entry.locations.map((location) => (
                            <span
                              key={`${entry.country}-${location}-${index}`}
                              className="ticker-chip"
                              style={{
                                "--ticker-accent": displayCountryColor(entry.country),
                                "--ticker-soft": hexToRgba(entry.color, 0.14),
                              }}
                            >
                              {location}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </article>

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
                          <TeamFlag
                            teamName={teamName}
                            className="team-flag team-flag-row"
                            fallbackClass="team-flag team-flag-row team-flag-fallback"
                            alt={`${teamName} flag`}
                          />
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
                <span>World Cup Awards</span>
                <span>post-simulation honors</span>
              </div>
              {awards ? (
                <div className="awards-stack">
                  <div className="awards-grid">
                    {awardEntries.map(([label, winner]) => (
                      <div
                        className="award-card"
                        key={label}
                        style={{
                          "--award-accent": displayCountryColor(winner?.team || winner?.country || ""),
                          "--award-soft": hexToRgba(countryColor(winner?.team || winner?.country || ""), 0.12),
                        }}
                      >
                        <span>{label}</span>
                        <strong>{winner?.player || "--"}</strong>
                        <small>{awardSubtitle(winner) || "No result"}</small>
                      </div>
                    ))}
                  </div>
                  <div className="allstar-panel">
                    <div className="panel-header compact">
                      <span>All-Star Team</span>
                      <span>{awards.allStarTeam?.length || 0} selections</span>
                    </div>
                    <div className="allstar-grid">
                      {(awards.allStarTeam || []).map((player) => (
                        <div
                          className="allstar-chip"
                          key={`${player.team}-${player.player}`}
                          style={{
                            "--award-accent": displayCountryColor(player.team || ""),
                            "--award-soft": hexToRgba(countryColor(player.team || ""), 0.12),
                          }}
                        >
                          <strong>{player.player}</strong>
                          <small>
                            {player.team} · {player.position}
                          </small>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <p className="empty-state">Run a simulation to award Golden Ball, Golden Boot, Golden Glove, Best Young Player, and the All-Star Team.</p>
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
                      <div className="group-card-top">
                        <p>Group {group.group}</p>
                        <span className="group-difficulty">
                          Average World Ranking: {formatAverageRanking(groupAverageRanking(group, teams))}
                        </span>
                      </div>
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
                  <div
                    className="team-hero"
                    style={{
                      "--team-accent": currentTeamTheme.accent,
                      "--team-banner": currentTeamTheme.banner,
                    }}
                  >
                    <TeamFlag
                      teamName={teamDetail.team.team_name}
                      className="team-badge team-badge-flag"
                      fallbackClass="team-badge"
                      alt={`${teamDetail.team.team_name} flag`}
                    />
                    <div className="team-hero-copy">
                      <h2>{teamDetail.team.team_name}</h2>
                      <span className="team-hero-tag">Group {teamDetail.team.group}</span>
                    </div>
                  </div>

                  <div className="rating-grid">
                    {[
                      ["overall", teamDetail.ratingBreakdown.squad],
                      ["attack", teamDetail.ratingBreakdown.attack],
                      ["midfield", teamDetail.ratingBreakdown.midfield],
                      ["defense", teamDetail.ratingBreakdown.defense],
                      ["goalkeeper", teamDetail.ratingBreakdown.goalkeeper],
                    ].map(([label, value]) => (
                      <div key={label} className="metric-card">
                        <span>{label}</span>
                        <strong>{formatMetricValue(value, true)}</strong>
                      </div>
                    ))}
                  </div>

                  <div className="subsection">
                    <div className="panel-header">
                      <span>Projected XI</span>
                      <span>{teamDetail.startingLineup?.formation || "4-3-3"}</span>
                    </div>
                    {lineupPlayers.length ? (
                      <div
                        className="pitch"
                        style={{
                          "--team-accent": currentTeamTheme.accent,
                          "--team-banner": currentTeamTheme.banner,
                        }}
                      >
                        <div className="pitch-lines" />
                        {lineupPlayers.map((player) => (
                          <div
                            key={`${player.position}-${player.name}`}
                            className="pitch-player"
                            style={{ left: `${player.coordinate.x}%`, top: `${player.coordinate.y}%` }}
                          >
                            <LineupPlayerTile player={player} teamName={teamDetail.team.team_name} />
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="empty-state">Projected lineup data is missing for this team profile.</p>
                    )}
                  </div>

                  <div className="subsection">
                    <div className="panel-header">
                      <span>X-Factors</span>
                      <span>{teamXFactorList.length} tagged players</span>
                    </div>
                    {teamXFactorList.length ? (
                      <>
                        {selectedProbabilities ? (
                          <p className="team-xfactor-note">
                            Projected title probability: {Math.round(selectedProbabilities.championProbability * 100)}%.
                          </p>
                        ) : null}
                        <div className="team-xfactor-grid">
                          {teamXFactorList.map((player) => (
                            <FootballCard
                              key={`${teamDetail.team.team_name}-${player.player}`}
                              player={player}
                              teamName={teamDetail.team.team_name}
                              reason={player.reason}
                              compact
                            />
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="empty-state">No tagged x-factors are assigned to this team yet.</p>
                    )}
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
                                <InitialsVisual label={player.short_name} />
                                <div className="player-copy">
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

        {activeTab === "Squad Comparison" ? (
          <section className="content-stack">
            <article className="panel">
              <div className="panel-header">
                <span>Squad Comparison</span>
                <span>{comparisonMode === "group" ? "group stage model" : "knockout model"}</span>
              </div>

              <div className="comparison-toolbar">
                <select value={compareTeamAId} onChange={(event) => setCompareTeamAId(event.target.value)}>
                  {teams.map((team) => (
                    <option key={`compare-a-${team.team_id}`} value={team.team_slug || teamSlug(team.team_name)}>
                      {team.team_name}
                    </option>
                  ))}
                </select>
                <select value={compareTeamBId} onChange={(event) => setCompareTeamBId(event.target.value)}>
                  {teams.map((team) => (
                    <option key={`compare-b-${team.team_id}`} value={team.team_slug || teamSlug(team.team_name)}>
                      {team.team_name}
                    </option>
                  ))}
                </select>
                <div className="comparison-toggle">
                  <button
                    className={comparisonMode === "knockout" ? "chip active" : "chip"}
                    onClick={() => setComparisonMode("knockout")}
                  >
                    Knockout
                  </button>
                  <button
                    className={comparisonMode === "group" ? "chip active" : "chip"}
                    onClick={() => setComparisonMode("group")}
                  >
                    Group Stage
                  </button>
                </div>
                <button onClick={handleRunComparison} disabled={comparisonLoading || !teams.length}>
                  {comparisonLoading ? "Comparing..." : "Compare Squads"}
                </button>
              </div>

              {comparisonError ? <p className="error-banner inline">{comparisonError}</p> : null}

              <div className="comparison-odds-grid">
                <div className="metric-card">
                  <span>{compareTeamADetail?.team?.team_name || "Team A"}</span>
                  <strong>{comparisonPercentages[0] || probabilityPercent(comparisonActive?.teamAWinProbability)}</strong>
                </div>
                {comparisonMode === "group" ? (
                  <div className="metric-card">
                    <span>Draw</span>
                    <strong>{comparisonPercentages[1] || probabilityPercent(comparisonActive?.drawProbability)}</strong>
                  </div>
                ) : null}
                <div className="metric-card">
                  <span>{compareTeamBDetail?.team?.team_name || "Team B"}</span>
                  <strong>
                    {comparisonMode === "group"
                      ? comparisonPercentages[2] || probabilityPercent(comparisonActive?.teamBWinProbability)
                      : comparisonPercentages[1] || probabilityPercent(comparisonActive?.teamBWinProbability)}
                  </strong>
                </div>
                <div className="metric-card">
                  <span>Projected Scoreline</span>
                  <strong>{comparisonActive?.mostLikelyScoreline || "--"}</strong>
                </div>
              </div>

              <div className="comparison-grid">
                {[compareTeamADetail, compareTeamBDetail].map((detail, index) => (
                  <article className="comparison-card" key={detail?.team?.team_name || `comparison-${index}`}>
                    <div className="comparison-card-head">
                      <div>
                        <strong>{detail?.team?.team_name || (index === 0 ? "Team A" : "Team B")}</strong>
                        <small>{detail?.startingLineup?.formation || "--"}</small>
                      </div>
                    </div>

                    <div className="comparison-rating-grid">
                      {[
                        ["Overall", detail?.ratingBreakdown?.squad],
                        ["Attack", detail?.ratingBreakdown?.attack],
                        ["Midfield", detail?.ratingBreakdown?.midfield],
                        ["Defense", detail?.ratingBreakdown?.defense],
                        ["Goalkeeper", detail?.ratingBreakdown?.goalkeeper],
                      ].map(([label, value]) => (
                        <div className="comparison-rating-pill" key={`${detail?.team?.team_name}-${label}`}>
                          <span>{label}</span>
                          <strong>{formatMetricValue(value, true)}</strong>
                        </div>
                      ))}
                    </div>

                    <div className="comparison-xfactor-block">
                      <span>Strongest X-Factors</span>
                      <p>
                        {(index === 0 ? comparisonTeamAXFactors : comparisonTeamBXFactors)
                          .slice(0, 3)
                          .map((player) => player.player || player.name)
                          .join(" · ") || "None tagged"}
                      </p>
                    </div>

                    <div className="comparison-lineup-list">
                      {(detail?.startingLineup?.players || []).map((player) => (
                        <div
                          className="comparison-lineup-row"
                          key={`${detail?.team?.team_name}-${player.position}-${player.name}`}
                        >
                          <span>{player.position}</span>
                          <strong>{player.name}</strong>
                          <small>OVR {ratingValue(player, null) ?? "--"}</small>
                        </div>
                      ))}
                    </div>
                  </article>
                ))}
              </div>
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
                  {["Round of 32", "Round of 16", "Quarter-final", "Semi-final", "Final"].map((round) => {
                    const matches =
                      round === "Final"
                        ? [...(bracketRounds["Final"] || []), ...(bracketRounds["Third Place Match"] || [])]
                        : bracketRounds[round] || [];
                    return (
                    <div className="round-column" key={round}>
                      <h3>{round}</h3>
                      {matches.map((match, index) => (
                        <div className="bracket-card" key={`${round}-${index}`}>
                          <p>{match.round}</p>
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
                  )})}
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
              <div className="football-card-grid">
                {xFactorShowcase.map((player) => (
                  <FootballCard
                    key={`${player.team}-${player.player}`}
                    player={player}
                    teamName={player.team}
                    reason={player.reason}
                  />
                ))}
              </div>
            </article>

          </section>
        ) : null}
      </div>
    </main>
  );
}
