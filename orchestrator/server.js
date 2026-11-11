// Knit orchestrator v0.3: clusters ("rooms") with invite codes.
//
//  Dashboard (master):  {type:"create_cluster"} -> {type:"cluster_created", code, token}
//                       {type:"resume", code, token}   (master reconnect after refresh)
//  Dashboard (viewer):  {type:"subscribe", code}
//  Worker agent:        {type:"register", code, id, ...profile}, then {type:"hb", id, ...}
//  Server -> worker:    {type:"ping", t}  worker answers {type:"pong", t}  -> rtt_ms
//  HTTP:                GET /cluster/<code>/nodes
const http = require("http");
const crypto = require("crypto");
const { WebSocketServer } = require("ws");

const PORT = process.env.PORT || 8080;
const DEAD_MS = 500;            // no heartbeat for this long -> dead
const FORGET_MS = 30000;        // drop dead nodes after this long
const TICK_MS = 100;
const PING_MS = 1000;
const ROOM_IDLE_MS = 10 * 60 * 1000;   // empty room (no master, no viewers, no live nodes) is deleted
const MAX_BAD_CODES = 5;        // wrong-code attempts per connection

// Models the dashboard can offer. layers = decoder layers, size_gb = fp32 weights.
const CATALOG = [
  { id: "qwen2.5-0.5b", name: "Qwen2.5 0.5B Instruct", hf: "Qwen/Qwen2.5-0.5B-Instruct", layers: 24, size_gb: 2.0 },
  { id: "qwen2.5-1.5b", name: "Qwen2.5 1.5B Instruct", hf: "Qwen/Qwen2.5-1.5B-Instruct", layers: 28, size_gb: 6.2 },
  { id: "qwen2.5-3b",   name: "Qwen2.5 3B Instruct",   hf: "Qwen/Qwen2.5-3B-Instruct",   layers: 36, size_gb: 12.4 },
];

const rooms = new Map();        // code -> room
const norm = (c) => String(c || "").trim().toUpperCase();

function newCode() {
  for (;;) {
    const code = `KNIT-${crypto.randomInt(1000, 10000)}-${String.fromCharCode(65 + crypto.randomInt(26))}`;
    if (!rooms.has(code)) return code;
  }
}

function createRoom() {
  const room = {
    code: newCode(),
    token: crypto.randomBytes(16).toString("hex"),   // proves "I am the master"
    nodes: new Map(),        // node id -> record
    sockets: new Map(),      // node id -> ws
    subs: new Set(),         // dashboards watching this room
    master: null,
    status: "idle",         // idle | loading | ready | degraded | error
    job: null,               // {model, name, hf, layers, plan:[{id,start,end}], pending:Set}
    error: null,
    lastActive: Date.now(),
  };
  rooms.set(room.code, room);
  return room;
}

const snapshot = (room) =>
  [...room.nodes.values()].sort((a, b) => (a.start ?? 1e9) - (b.start ?? 1e9) || String(a.id).localeCompare(String(b.id)));

const send = (ws, obj) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(obj)); };

const stateMsg = (room) => ({
  type: "state", code: room.code, nodes: snapshot(room), status: room.status,
  model: room.job ? room.job.name : null, error: room.error,
  progress: room.job ? { done: room.job.plan.length - room.job.pending.size, total: room.job.plan.length } : { done: 0, total: 0 },
});

// contiguous layer ranges proportional to capacity (largest remainder), at least 1 layer each
function splitLayers(L, caps) {
  const tot = caps.reduce((a, b) => a + b, 0);
  const ideal = caps.map((c) => (c / tot) * L);
  const cnt = ideal.map((x) => Math.max(1, Math.floor(x)));
  let sum = cnt.reduce((a, b) => a + b, 0);
  while (sum < L) { let i = 0; ideal.forEach((x, j) => { if (x - cnt[j] > ideal[i] - cnt[i]) i = j; }); cnt[i]++; sum++; }
  while (sum > L) { let i = -1; cnt.forEach((c, j) => { if (c > 1 && (i < 0 || c - ideal[j] > cnt[i] - ideal[i])) i = j; }); cnt[i]--; sum--; }
  const out = []; let st = 0;
  for (const c of cnt) { out.push([st, st + c]); st += c; }
  return out;
}

const server = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  const m = /^\/cluster\/([^/]+)\/nodes$/.exec(req.url.split("?")[0]);
  if (m) {
    const room = rooms.get(norm(decodeURIComponent(m[1])));
    if (!room) return res.writeHead(404).end();
    res.setHeader("content-type", "application/json");
    return res.end(JSON.stringify(snapshot(room)));
  }
  const mi = /^\/cluster\/([^/]+)\/info$/.exec(req.url.split("?")[0]);
  if (mi) {
    const room = rooms.get(norm(decodeURIComponent(mi[1])));
    if (!room) return res.writeHead(404).end();
    res.setHeader("content-type", "application/json");
    const j = room.job;
    return res.end(JSON.stringify({ status: room.status, model: j && j.model, name: j && j.name, hf: j && j.hf, layers: j && j.layers, plan: j ? j.plan : [] }));
  }
  if (req.url === "/health") return res.end("ok");
  res.writeHead(404).end();
});

const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  let room = null, nodeId = null, bad = 0;

  const reject = (message, fatal) => {
    send(ws, { type: "error", message });
    if (fatal || ++bad >= MAX_BAD_CODES) setTimeout(() => ws.close(), 50);
  };
  const watch = (r, master) => {
    room = r;
    r.subs.add(ws);
    if (master) r.master = ws;
    send(ws, { type: "joined", code: r.code, master });
    if (master) send(ws, { type: "catalog", models: CATALOG });
    send(ws, stateMsg(r));
  };

  ws.on("message", (raw) => {
    let m;
    try { m = JSON.parse(raw); } catch { return; }

    if (m.type === "create_cluster" && !room) {
      const r = createRoom();
      watch(r, true);
      send(ws, { type: "cluster_created", code: r.code, token: r.token });
    } else if (m.type === "resume" && !room) {
      const r = rooms.get(norm(m.code));
      if (!r || r.token !== m.token) return reject("Cluster expired or unknown. Create a new one.");
      watch(r, true);
    } else if (m.type === "subscribe" && !room) {
      const r = rooms.get(norm(m.code));
      if (!r) return reject("Unknown cluster code.");
      watch(r, false);
    } else if (m.type === "register" && !room) {
      const r = rooms.get(norm(m.code));
      if (!r) return reject("Unknown cluster code.", true);
      if (!m.id) return reject("Missing node id.", true);
      const { type, code, ...rest } = m;
      room = r; nodeId = String(m.id);
      r.nodes.set(nodeId, { ...rest, joinedAt: Date.now(), lastSeen: Date.now(), status: "alive", rtt_ms: null });
      r.sockets.set(nodeId, ws);
      send(ws, { type: "registered", code: r.code });
    } else if (m.type === "hb" && room && nodeId && m.id === nodeId) {
      const n = room.nodes.get(nodeId);
      if (n) { const { type, code, id, ...rest } = m; Object.assign(n, rest, { lastSeen: Date.now(), status: "alive" }); }
    } else if (m.type === "start_cluster" && room && room.master === ws) {
      const warn = (message) => send(ws, { type: "error", message });
      const spec = CATALOG.find((c) => c.id === m.model);
      const k = Math.floor(Number(m.nodes));
      const alive = [...room.nodes.values()].filter((n) => n.status === "alive" && room.sockets.has(n.id))
        .sort((a, b) => (b.capacity || 0) - (a.capacity || 0));
      if (room.status === "loading") return warn("Already loading. Wait for it to finish.");
      if (!spec) return warn("Unknown model.");
      if (!(k >= 1) || k > spec.layers) return warn("Pick a valid number of PCs.");
      if (alive.length < k) return warn(`Only ${alive.length} worker(s) joined.`);
      const chosen = alive.slice(0, k);
      const ranges = splitLayers(spec.layers, chosen.map((n) => n.capacity || 1));
      const plan = chosen.map((n, i) => ({ id: n.id, start: ranges[i][0], end: ranges[i][1] }));
      room.job = { model: spec.id, name: spec.name, hf: spec.hf, layers: spec.layers, plan, pending: new Set(plan.map((p) => p.id)) };
      room.status = "loading"; room.error = null;
      for (const p of plan) send(room.sockets.get(p.id), { type: "load", model: spec.hf, start: p.start, end: p.end });
      for (const n of alive.slice(k)) if (n.start != null) send(room.sockets.get(n.id), { type: "unload" });
    } else if (m.type === "loaded" && room && nodeId && room.job) {
      room.job.pending.delete(nodeId);
      if (room.status === "loading" && room.job.pending.size === 0) room.status = "ready";
    } else if (m.type === "load_failed" && room && nodeId && room.job) {
      room.status = "error"; room.error = String(m.error || "load failed").slice(0, 200);
    } else if (m.type === "pong" && room && nodeId) {
      const n = room.nodes.get(nodeId);
      const rtt = performance.now() - Number(m.t);
      if (n && rtt >= 0 && rtt < 60000) n.rtt_ms = Math.round((n.rtt_ms == null ? rtt : 0.8 * n.rtt_ms + 0.2 * rtt) * 10) / 10;
    }
  });

  ws.on("close", () => {
    if (!room) return;
    room.subs.delete(ws);
    if (room.master === ws) room.master = null;
    if (nodeId && room.sockets.get(nodeId) === ws) {
      const n = room.nodes.get(nodeId);
      if (n) n.status = "dead";
    }
  });
});

setInterval(() => {
  const now = performance.now();
  for (const room of rooms.values())
    for (const [id, ws] of room.sockets) send(ws, { type: "ping", t: now });
}, PING_MS);

setInterval(() => {
  const now = Date.now();
  for (const [code, room] of rooms) {
    let anyAlive = false;
    for (const [id, n] of room.nodes) {
      if (n.status === "alive" && now - n.lastSeen > DEAD_MS) n.status = "dead";
      if (n.status === "dead" && now - n.lastSeen > FORGET_MS) { room.nodes.delete(id); room.sockets.delete(id); }
      if (n.status === "alive") anyAlive = true;
    }
    if (room.job && (room.status === "ready" || room.status === "degraded")) {
      const ok = room.job.plan.every((p) => { const n = room.nodes.get(p.id); return n && n.status === "alive"; });
      room.status = ok ? "ready" : "degraded";
    }
    if (room.master || room.subs.size || anyAlive) room.lastActive = now;
    else if (now - room.lastActive > ROOM_IDLE_MS) { rooms.delete(code); continue; }
    if (room.subs.size) {
      const msg = JSON.stringify(stateMsg(room));
      for (const d of room.subs) if (d.readyState === 1) d.send(msg);
    }
  }
}, TICK_MS);

server.listen(PORT, () => console.log(`Knit orchestrator v0.3 on :${PORT}`));