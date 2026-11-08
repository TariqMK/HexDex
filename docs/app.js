// HexDex product page: live previews with sample data, OS-detected downloads and the latest release from GitHub.
"use strict";

const REPO = "TariqMK/HexDex";
const ASSET = { windows: /windows-x64\.zip$/i, macos: /macos-arm64\.zip$/i, linux: /linux-x64\.tar\.gz$/i };
const OS_NAME = { windows: "Windows", macos: "macOS", linux: "Linux" };
const STILL = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const TYPE = {
  normal: "#9099A1", fire: "#FF7C33", water: "#3B9EDC", electric: "#F8CF00", grass: "#5FBF30",
  ice: "#74CEC0", fighting: "#CE3F2A", poison: "#A95FAB", ground: "#D6A83A", flying: "#8899D4",
  psychic: "#F85888", bug: "#A8B820", rock: "#B8A038", ghost: "#8A6FBF", dragon: "#8A5CF8",
  dark: "#8A8780", steel: "#B8B8D0", fairy: "#F0A0FF",
};

/* Generic creature silhouettes in the app icon's style: a solid hexagon in the type colour with
   a dark shape built from smooth ellipses. Every shape shares the icon's round body. No game artwork. */
const INK = "#141415";
const BODY = '<ellipse cx="50" cy="60" rx="20" ry="18"/>';
const pair = (x, y, rx, ry, deg) =>
  `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" transform="rotate(${deg} ${x} ${y})"/>` +
  `<ellipse cx="${100 - x}" cy="${y}" rx="${rx}" ry="${ry}" transform="rotate(${-deg} ${100 - x} ${y})"/>`;
const SHAPES = {
  round: BODY + pair(36.5, 40, 6.7, 10.5, -20),
  pointed: BODY + pair(35, 38, 5, 13, -14),
  horned: BODY + pair(41, 35, 3, 11, -8),
  bear: '<ellipse cx="50" cy="58" rx="24" ry="20"/>' + pair(34, 40, 6, 6, 0),
  crest: BODY + '<ellipse cx="50" cy="33" rx="4" ry="10"/>' + pair(39, 37, 3.5, 8.5, -26),
  winged: BODY + '<ellipse cx="50" cy="36" rx="4" ry="8"/>' + pair(26, 52, 12, 6.5, 28),
  finned: BODY + '<ellipse cx="50" cy="33" rx="5" ry="11"/>' + pair(27, 64, 8.5, 4.5, -22),
  egg: '<path d="M50 24c11 0 19 17 19 29 0 12-8 19-19 19s-19-7-19-19c0-12 8-29 19-29z"/>',
};
const HEX = "50,10 84.6,30 84.6,70 50,90 15.4,70 15.4,30";
function art(shape, type) {
  const c = TYPE[type] || "#888";
  return `<svg class="art" viewBox="0 0 100 100" aria-hidden="true"><polygon points="${HEX}" fill="${c}" stroke="${c}" stroke-width="10" stroke-linejoin="round"/><g fill="${INK}">${SHAPES[shape]}</g></svg>`;
}
const icon = (id, cls = "") => `<svg class="ic ${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;

/* ---- Hero: collection grid with filters ---- */
const COLLECTION = [
  { id: 1, name: "Bulbasaur", gen: 4, lv: 14, type: "grass", shape: "bear" },
  { id: 6, name: "Charizard", gen: 4, lv: 62, type: "fire", shape: "winged", shiny: true, fav: true, note: true, files: 2 },
  { id: 25, name: "Pikachu", gen: 4, lv: 34, type: "electric", shape: "round" },
  { id: 59, name: "Arcanine", gen: 4, lv: 55, type: "fire", shape: "pointed" },
  { id: 94, name: "Gengar", gen: 4, lv: 58, type: "ghost", shape: "pointed" },
  { id: 130, name: "Gyarados", gen: 4, lv: 48, type: "water", shape: "finned", shiny: true, fav: true, note: true },
  { id: 131, name: "Lapras", gen: 4, lv: 40, type: "water", shape: "finned" },
  { id: 133, name: "Egg (Eevee)", gen: 4, lv: 1, type: "normal", shape: "egg", egg: true },
  { id: 143, name: "Snorlax", gen: 4, lv: 50, type: "normal", shape: "bear" },
  { id: 149, name: "Dragonite", gen: 4, lv: 64, type: "dragon", shape: "winged" },
  { id: 150, name: "Mewtwo", gen: 4, lv: 70, type: "psychic", shape: "horned", legend: true, note: true },
  { id: 197, name: "Umbreon", gen: 4, lv: 44, type: "dark", shape: "pointed" },
  { id: 249, name: "Lugia", gen: 4, lv: 45, type: "psychic", shape: "winged", legend: true },
  { id: 445, name: "Garchomp", gen: 4, lv: 66, type: "dragon", shape: "crest", fav: true, note: true },
  { id: 448, name: "Lucario", gen: 4, lv: 48, type: "fighting", shape: "pointed", note: true },
  { id: 658, name: "Greninja", gen: 6, lv: 60, type: "water", shape: "crest", fav: true, note: true },
  { id: 700, name: "Sylveon", gen: 6, lv: 42, type: "fairy", shape: "round" },
  { id: 716, name: "Xerneas", gen: 6, lv: 50, type: "fairy", shape: "horned", legend: true },
];
const pad = n => String(n).padStart(3, "0");
const grid = document.getElementById("appGrid");
grid.innerHTML = COLLECTION.map(p => `
  <div class="card${p.name === "Charizard" ? " active" : ""}" data-id="${p.id}">
    <div class="card-top"><span>#${pad(p.id)} · G${p.gen}</span>${icon("star", p.fav ? "on" : "")}</div>
    ${art(p.shape, p.type)}
    <div class="card-name">${p.name}</div>
    <div class="card-foot"><span>Lv ${p.lv}</span>${p.shiny ? icon("spark", "shiny") : ""}${p.note ? icon("note") : ""}${p.files ? `<span>×${p.files}</span>` : ""}</div>
  </div>`).join("");

const cards = [...grid.children];
const chips = [...document.querySelectorAll(".chip[data-filter]")];
const small = window.matchMedia("(max-width: 720px)");
let active = new Set();

function applyFilters(animate) {
  let shown = 0;
  const limit = small.matches ? 9 : 18;
  COLLECTION.forEach((p, i) => {
    const keep = [...active].every(f => p[f]);
    const card = cards[i];
    const wasOut = card.classList.contains("out");
    card.classList.toggle("out", !keep);
    card.classList.toggle("over", keep && shown >= limit);
    if (keep) {
      shown++;
      // Only cards coming back animate; cards already on screen stay still.
      if (animate && wasOut) { card.classList.remove("enter"); void card.offsetWidth; card.classList.add("enter"); }
    }
  });
  const total = COLLECTION.filter(p => [...active].every(f => p[f])).length;
  document.getElementById("appCount").textContent = `${total} Pokémon`;
  chips.forEach(c => c.setAttribute("aria-pressed", active.has(c.dataset.filter)));
}
small.addEventListener("change", () => applyFilters(false));

let userTookOver = false;
chips.forEach(chip => chip.addEventListener("click", () => {
  userTookOver = true;
  const f = chip.dataset.filter;
  active.has(f) ? active.delete(f) : active.add(f);
  applyFilters(true);
}));
applyFilters(false);

/* A short tour of the filters until the visitor clicks one. */
const TOUR = [[], [], ["shiny"], [], [], ["fav"], [], [], ["legend"]];
let tourStep = 0;

/* ---- Stat hexagon ---- */
const AXES = [["hp", "HP"], ["atk", "Atk"], ["def", "Def"], ["spe", "Spe"], ["spd", "SpD"], ["spa", "SpA"]];
const NATURE_NAME = { atk: "Attack", def: "Defense", spe: "Speed", spd: "Sp. Def", spa: "Sp. Atk" };
const MONS = [
  { name: "Charizard", id: 6, lv: 62, types: ["fire", "flying"], nature: ["Timid", "spe", "atk"],
    base: { hp: 78, atk: 84, def: 78, spe: 100, spd: 85, spa: 109 }, iv: { hp: 31, atk: 28, def: 30, spe: 31, spd: 29, spa: 24 }, ev: { hp: 6, atk: 0, def: 0, spe: 252, spd: 0, spa: 252 } },
  { name: "Garchomp", id: 445, lv: 66, types: ["dragon", "ground"], nature: ["Jolly", "spe", "spa"],
    base: { hp: 108, atk: 130, def: 95, spe: 102, spd: 85, spa: 80 }, iv: { hp: 31, atk: 31, def: 27, spe: 31, spd: 22, spa: 12 }, ev: { hp: 4, atk: 252, def: 0, spe: 252, spd: 0, spa: 0 } },
  { name: "Gengar", id: 94, lv: 58, types: ["ghost", "poison"], nature: ["Modest", "spa", "atk"],
    base: { hp: 60, atk: 65, def: 60, spe: 110, spd: 75, spa: 130 }, iv: { hp: 24, atk: 9, def: 18, spe: 30, spd: 26, spa: 31 }, ev: { hp: 0, atk: 0, def: 0, spe: 252, spd: 4, spa: 252 } },
  { name: "Snorlax", id: 143, lv: 50, types: ["normal"], nature: ["Careful", "spd", "spa"],
    base: { hp: 160, atk: 110, def: 65, spe: 30, spd: 110, spa: 65 }, iv: { hp: 31, atk: 25, def: 31, spe: 3, spd: 31, spa: 14 }, ev: { hp: 252, atk: 4, def: 0, spe: 0, spd: 252, spa: 0 } },
  { name: "Sylveon", id: 700, lv: 42, types: ["fairy"], nature: ["Calm", "spd", "atk"],
    base: { hp: 95, atk: 65, def: 65, spe: 60, spd: 130, spa: 110 }, iv: { hp: 29, atk: 6, def: 20, spe: 17, spd: 31, spa: 28 }, ev: { hp: 252, atk: 0, def: 4, spe: 0, spd: 0, spa: 252 } },
  { name: "Lucario", id: 448, lv: 48, types: ["fighting", "steel"], nature: ["Adamant", "atk", "spa"],
    base: { hp: 70, atk: 110, def: 70, spe: 90, spd: 70, spa: 115 }, iv: { hp: 21, atk: 31, def: 16, spe: 30, spd: 19, spa: 8 }, ev: { hp: 0, atk: 252, def: 6, spe: 252, spd: 0, spa: 0 } },
];
const R = 72, MAX = 160;
const pt = (k, r) => { const a = -Math.PI / 2 + k * Math.PI / 3; return [Math.cos(a) * r, Math.sin(a) * r]; };
const hexSvg = document.getElementById("statHex");
const ring = f => AXES.map((_, k) => pt(k, R * f).map(n => n.toFixed(1)).join(",")).join(" ");
hexSvg.innerHTML =
  [.25, .5, .75, 1].map(f => `<polygon class="ring" points="${ring(f)}"/>`).join("") +
  AXES.map((_, k) => { const [x, y] = pt(k, R); return `<line class="axis" x1="0" y1="0" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`; }).join("") +
  `<polygon class="shape" id="hexShape"/>` +
  AXES.map((_, k) => `<circle class="dot" r="2" id="hexDot${k}"/>`).join("") +
  AXES.map((_, k) => { const [x, y] = pt(k, R + 14); const anchor = Math.abs(x) < 1 ? "middle" : x > 0 ? "start" : "end"; return `<text x="${x.toFixed(1)}" y="${(y + 3).toFixed(1)}" text-anchor="${anchor}" id="hexLabel${k}"></text>`; }).join("");

function calc(m, key) {
  const core = Math.floor((2 * m.base[key] + m.iv[key] + Math.floor(m.ev[key] / 4)) * m.lv / 100);
  if (key === "hp") return core + m.lv + 10;
  const mod = m.nature[1] === key ? 1.1 : m.nature[2] === key ? 0.9 : 1;
  return Math.floor((core + 5) * mod);
}
let hexIndex = 0, hexFrom = MONS[0].base;
function drawShape(base) {
  const pts = AXES.map(([key], k) => pt(k, R * Math.min(base[key], MAX) / MAX));
  document.getElementById("hexShape").setAttribute("points", pts.map(p => p.map(n => n.toFixed(1)).join(",")).join(" "));
  pts.forEach(([x, y], k) => { const d = document.getElementById("hexDot" + k); d.setAttribute("cx", x.toFixed(1)); d.setAttribute("cy", y.toFixed(1)); });
}
function showMon(m, animate) {
  hexSvg.style.setProperty("--tc", TYPE[m.types[0]]);
  hexSvg.setAttribute("aria-label", "Base stats: " + AXES.map(([k, l]) => `${l} ${m.base[k]}`).join(", "));
  document.getElementById("hexName").textContent = m.name;
  document.getElementById("hexDex").textContent = `#${pad(m.id)} · Lv ${m.lv} · ${m.nature[0]}`;
  document.getElementById("hexTypes").innerHTML = m.types.map(t => `<span class="type"><i style="background:${TYPE[t]}"></i>${t}</span>`).join("");
  AXES.forEach(([k, l], i) => { document.getElementById("hexLabel" + i).textContent = `${l} ${m.base[k]}`; });
  const rows = AXES.map(([k, l]) => {
    const mark = m.nature[1] === k ? " +" : m.nature[2] === k ? " −" : "";
    return `<tr><td>${l}${mark}</td><td>${m.base[k]}</td><td>${m.iv[k]}</td><td>${m.ev[k]}</td><td class="total">${calc(m, k)}</td></tr>`;
  }).join("");
  document.getElementById("statTable").innerHTML = `<thead><tr><th>Stat</th><th>Base</th><th>IV</th><th>EV</th><th>Lv ${m.lv}</th></tr></thead><tbody>${rows}</tbody>`;
  if (!animate) { drawShape(m.base); hexFrom = m.base; return; }
  const from = hexFrom, start = performance.now();
  const step = now => {
    const t = Math.min((now - start) / 600, 1), e = 1 - Math.pow(1 - t, 3);
    const mid = {}; AXES.forEach(([k]) => { mid[k] = from[k] + (m.base[k] - from[k]) * e; });
    drawShape(mid);
    if (t < 1) requestAnimationFrame(step); else hexFrom = m.base;
  };
  requestAnimationFrame(step);
}
showMon(MONS[0], false);

/* ---- Evolution chains ---- */
const CHAINS = [
  { current: 2, nodes: [["Charmander", 4, "fire", "crest"], ["Charmeleon", 5, "fire", "crest"], ["Charizard", 6, "fire", "winged"]], how: ["Lv 16", "Lv 36"] },
  { current: 1, nodes: [["Pichu", 172, "electric", "round"], ["Pikachu", 25, "electric", "round"], ["Raichu", 26, "electric", "round"]], how: ["Friendship", "Thunder Stone"] },
  { current: 2, nodes: [["Gastly", 92, "ghost", "bear"], ["Haunter", 93, "ghost", "pointed"], ["Gengar", 94, "ghost", "pointed"]], how: ["Lv 25", "Trade"] },
  { current: 2, nodes: [["Gible", 443, "dragon", "crest"], ["Gabite", 444, "dragon", "crest"], ["Garchomp", 445, "dragon", "crest"]], how: ["Lv 24", "Lv 48"] },
  { current: 0, nodes: [["Froakie", 656, "water", "round"], ["Frogadier", 657, "water", "crest"], ["Greninja", 658, "water", "crest"]], how: ["Lv 16", "Lv 36"] },
];
let evoIndex = 0;
const evoEl = document.getElementById("evo");
function showChain(c, animate) {
  evoEl.innerHTML = c.nodes.map(([name, id, type, shape], i) =>
    (i ? `<div class="evo-arrow">${icon("arrow")}<span>${c.how[i - 1]}</span></div>` : "") +
    `<div class="evo-node${i === c.current ? " current" : ""}">${art(shape, type)}<span class="evo-name">${name}</span><span class="evo-dex">#${pad(id)}</span></div>`
  ).join("");
  if (animate) { evoEl.classList.remove("swap"); void evoEl.offsetWidth; evoEl.classList.add("swap"); }
}
showChain(CHAINS[0], false);

/* ---- Scan progress: a first scan of 25 files, with one slow request ---- */
const FILES = ["001 - Bulbasaur - 3A7C", "006 - Charizard - 51D0", "006 - Charizard - 9E21", "025 - Pikachu - 7B44", "059 - Arcanine - 0C9F",
  "094 - Gengar - E301", "130 - Gyarados - 2D8A", "131 - Lapras - 6F12", "133 - Eevee - 44B0", "143 - Snorlax - A9C3", "149 - Dragonite - 1E77",
  "150 - Mewtwo - C0DE", "197 - Umbreon - 8A10", "248 - Tyranitar - 5F3E", "249 - Lugia - 0A49", "282 - Gardevoir - 3C5D", "393 - Piplup - D002",
  "445 - Garchomp - 7710", "448 - Lucario - B6A2", "658 - Greninja - 2F6D91A0C1B3", "661 - Fletchling - 81E4C02A77D0", "681 - Aegislash - 4B30E9D1F2A6",
  "700 - Sylveon - 9D17A64B0E52", "704 - Goomy - C2A8F1306B9E", "716 - Xerneas - 07F2B9E4D1C3"];
const scan = { done: 0, seconds: 0, log: [], wait: null, pause: 0, phase: 0 };
const ext = f => (f.length > 20 ? ".pk6" : ".pk4");
function scanRender() {
  const time = `${Math.floor(scan.seconds / 60)}m ${scan.seconds % 60}s`;
  const file = FILES[Math.min(scan.done, FILES.length - 1)];
  const finished = scan.done >= FILES.length;
  const message = finished ? `Finished: ${FILES.length} loaded, 0 file errors` : scan.wait !== null ? `Downloading moves for ${file.split(" - ")[1]}` : `Reading ${file}${ext(file)}`;
  const waiting = scan.wait !== null ? ` · waiting ${scan.wait}s` : "";
  document.getElementById("scanText").textContent = `${scan.done}/${FILES.length} files · ${time} · ${message}${waiting}`;
  document.getElementById("scanBar").style.width = `${(scan.done / FILES.length) * 100}%`;
  document.getElementById("scanLog").textContent = scan.log.slice(-4).join("\n");
}
function scanTick() {
  if (scan.pause > 0) { if (--scan.pause === 0) Object.assign(scan, { done: 0, seconds: 0, log: ["Found 25 Pokémon files"], wait: null }); scanRender(); return; }
  scan.seconds++;
  const file = FILES[scan.done];
  if (scan.done === 11 && scan.wait === null && !scan.slowDone) { scan.wait = 0; scan.log.push(`Requesting moves for ${file.split(" - ")[1]}`); }
  if (scan.wait !== null) {
    scan.wait++;
    if (scan.wait > 4) { scan.wait = null; scan.slowDone = true; scan.log.push(`Request finished after 5s`); }
    scanRender(); return;
  }
  const n = 1 + (Math.random() < 0.5 ? 1 : 0);
  for (let i = 0; i < n && scan.done < FILES.length; i++) {
    const f = FILES[scan.done];
    scan.log.push(`Loaded ${f.split(" - ")[1]} #${f.slice(0, 3)}`);
    scan.done++;
  }
  if (scan.done >= FILES.length) { scan.log.push(`Finished: ${FILES.length} loaded, 0 file errors`); scan.pause = 5; scan.slowDone = false; }
  scanRender();
}
scan.log = ["Found 25 Pokémon files"];
scanRender();

/* ---- One clock for every preview. Paused while the tab is hidden; off with reduced motion. ---- */
if (STILL) {
  Object.assign(scan, { done: 14, seconds: 23 });
  scan.log.push("Loaded Snorlax #143", "Loaded Dragonite #149", "Loaded Mewtwo #150");
  scanRender();
} else {
  let tick = 0;
  setInterval(() => {
    if (document.hidden) return;
    tick++;
    scanTick();
    if (tick % 3 === 0 && !userTookOver) { tourStep = (tourStep + 1) % TOUR.length; active = new Set(TOUR[tourStep]); applyFilters(true); }
    if (tick % 4 === 0) { hexIndex = (hexIndex + 1) % MONS.length; showMon(MONS[hexIndex], true); }
    if (tick % 5 === 2) { evoIndex = (evoIndex + 1) % CHAINS.length; showChain(CHAINS[evoIndex], true); }
  }, 1000);
}

/* ---- Downloads ---- */
function detectOS() {
  const ua = navigator.userAgent;
  if (/Android|iPhone|iPad|iPod/i.test(ua)) return null;
  const p = (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || ua;
  if (/Win/i.test(p)) return "windows";
  if (/Mac/i.test(p)) return "macos";
  if (/Linux|X11/i.test(p)) return "linux";
  return null;
}
const os = detectOS();
const heroBtn = document.getElementById("heroDownload");
if (os) {
  document.getElementById("heroDownloadText").textContent = `Download for ${OS_NAME[os]}`;
  document.querySelector(`.dl[data-os="${os}"]`).classList.add("mine");
}

fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
  .then(r => (r.ok ? r.json() : Promise.reject(r.status)))
  .then(rel => {
    const date = new Date(rel.published_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
    document.getElementById("heroVersion").textContent = rel.tag_name;
    document.getElementById("appVer").textContent = rel.tag_name;
    document.getElementById("dlVersion").textContent = `${rel.tag_name} · ${date}`;
    for (const asset of rel.assets || []) {
      for (const [key, pattern] of Object.entries(ASSET)) {
        if (!pattern.test(asset.name)) continue;
        const card = document.querySelector(`.dl[data-os="${key}"]`);
        card.href = asset.browser_download_url;
        card.querySelector(".dl-size").textContent = `${Math.round(asset.size / 1048576)} MB`;
        if (key === os) heroBtn.href = asset.browser_download_url;
      }
    }
  })
  .catch(() => { /* Offline, rate-limited or no release: every link already points to the Releases page. */ });
