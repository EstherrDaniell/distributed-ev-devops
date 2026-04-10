# allocator.py — Central Allocator Server
# This is the "brain" of the distributed system.
# It:
#   1. Knows about all station nodes
#   2. Fetches their status (handles failures gracefully)
#   3. Picks the best available station for a new request
#   4. Serves the frontend dashboard

import requests
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── Station Registry ──────────────────────────────────────────────────────────
# Add or remove stations here. Each entry is a separate process/service.
STATIONS = [
    {"id": "station_1", "url": "http://localhost:5001"},
    {"id": "station_2", "url": "http://localhost:5002"},
    {"id": "station_3", "url": "http://localhost:5003"},
]

TIMEOUT = 2  # seconds to wait before declaring a station offline


# ── Helper: fetch status from one station ────────────────────────────────────
def fetch_station_status(station):
    """
    Try to contact a station. If it's unreachable, mark it offline.
    This is our fault-tolerance mechanism — one station down ≠ system down.
    """
    try:
        resp = requests.get(f"{station['url']}/status", timeout=TIMEOUT)
        data = resp.json()
        data["online"] = True
        data["url"] = station["url"]
        return data
    except Exception:
        # Station is offline or unreachable — return a safe fallback
        return {
            "id": station["id"],
            "name": station["id"].replace("_", " ").title(),
            "location": "Unknown",
            "total_slots": 0,
            "available_slots": 0,
            "online": False,
            "url": station["url"],
        }


# ── API: get all station statuses ────────────────────────────────────────────
@app.route("/api/stations", methods=["GET"])
def get_all_stations():
    """Collect status from every registered station in parallel (simple loop)."""
    statuses = [fetch_station_status(s) for s in STATIONS]
    return jsonify(statuses)


# ── API: request a charging slot ─────────────────────────────────────────────
@app.route("/api/request-slot", methods=["POST"])
def request_slot():
    """
    Allocation logic:
      1. Ask every station for its current status.
      2. Filter to online stations that have at least 1 free slot.
      3. Pick the one with the MOST available slots (greedy best-fit).
      4. Tell that station to book a slot.
      5. Return the result to the user.
    """
    statuses = [fetch_station_status(s) for s in STATIONS]

    # Keep only stations that are online and have free slots
    available = [s for s in statuses if s["online"] and s["available_slots"] > 0]

    if not available:
        return jsonify({
            "success": False,
            "message": "❌ No slots available at any station right now.",
        }), 503

    # Pick the station with the most free slots (simple load-balancing)
    best = max(available, key=lambda s: s["available_slots"])

    try:
        resp = requests.post(f"{best['url']}/book", timeout=TIMEOUT)
        result = resp.json()
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": f"✅ Slot allocated at {best['name']} ({best['location']})",
                "station": best["name"],
                "remaining_slots": result["remaining_slots"],
            })
        else:
            return jsonify({"success": False, "message": result.get("message", "Booking failed")}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Station error: {str(e)}"}), 500


# ── API: release a slot (for demo / testing) ─────────────────────────────────
@app.route("/api/release-slot/<station_id>", methods=["POST"])
def release_slot(station_id):
    """Release a slot at a specific station. Useful for demo resets."""
    station = next((s for s in STATIONS if s["id"] == station_id), None)
    if not station:
        return jsonify({"success": False, "message": "Station not found"}), 404
    try:
        resp = requests.post(f"{station['url']}/release", timeout=TIMEOUT)
        return jsonify(resp.json())
    except Exception:
        return jsonify({"success": False, "message": "Station offline"}), 503


# ── Frontend Dashboard ────────────────────────────────────────────────────────
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>EV Charging Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    /* ── Reset & base ─────────────────────────────────── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:        #0d1117;
      --surface:   #161b22;
      --surface2:  #21262d;
      --border:    #30363d;
      --text:      #e6edf3;
      --muted:     #8b949e;
      --green:     #3fb950;
      --green-dim: #1a3726;
      --red:       #f85149;
      --red-dim:   #3d1a19;
      --blue:      #58a6ff;
      --blue-dim:  #1a2f4a;
      --yellow:    #d29922;
      --accent:    #238636;
      --radius:    14px;
      --shadow:    0 8px 32px rgba(0,0,0,.45);
    }

    body {
      font-family: 'DM Sans', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 40px 20px 80px;
      background-image:
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(35,134,54,.18) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 80% 90%, rgba(88,166,255,.08) 0%, transparent 50%);
    }

    /* ── Layout wrapper ───────────────────────────────── */
    .container {
      max-width: 900px;
      margin: 0 auto;
    }

    /* ── Header ───────────────────────────────────────── */
    header {
      text-align: center;
      margin-bottom: 48px;
    }
    .logo-row {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin-bottom: 10px;
    }
    .logo-icon {
      width: 48px; height: 48px;
      background: linear-gradient(135deg, #238636, #3fb950);
      border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-size: 24px;
      box-shadow: 0 0 24px rgba(63,185,80,.35);
    }
    h1 {
      font-family: 'Space Grotesk', sans-serif;
      font-size: clamp(1.6rem, 4vw, 2.4rem);
      font-weight: 700;
      letter-spacing: -0.5px;
      background: linear-gradient(135deg, #e6edf3 30%, #58a6ff);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    .subtitle {
      color: var(--muted);
      font-size: .95rem;
      font-weight: 400;
      margin-top: 6px;
    }

    /* ── Network status bar ───────────────────────────── */
    .net-bar {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 30px;
      padding: 8px 20px;
      width: fit-content;
      margin: 18px auto 0;
      font-size: .82rem;
      color: var(--muted);
    }
    .pulse {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 0 0 rgba(63,185,80,.6);
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0%   { box-shadow: 0 0 0 0 rgba(63,185,80,.6); }
      70%  { box-shadow: 0 0 0 8px rgba(63,185,80,0); }
      100% { box-shadow: 0 0 0 0 rgba(63,185,80,0); }
    }

    /* ── Section headings ─────────────────────────────── */
    .section-label {
      font-size: .75rem;
      font-weight: 600;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 16px;
    }

    /* ── Station grid ─────────────────────────────────── */
    .stations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
      margin-bottom: 36px;
    }

    /* ── Station card ─────────────────────────────────── */
    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
      transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
      position: relative;
      overflow: hidden;
    }
    .card::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: linear-gradient(90deg, var(--green), var(--blue));
      opacity: 0;
      transition: opacity .3s;
    }
    .card:hover {
      transform: translateY(-3px);
      box-shadow: var(--shadow);
      border-color: #484f58;
    }
    .card:hover::before { opacity: 1; }
    .card.offline {
      opacity: .7;
      border-color: var(--red-dim);
    }
    .card.offline::before {
      background: var(--red);
      opacity: 1;
    }

    .card-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 18px;
    }
    .card-icon {
      width: 40px; height: 40px;
      border-radius: 10px;
      background: var(--green-dim);
      border: 1px solid rgba(63,185,80,.25);
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
    }
    .card.offline .card-icon {
      background: var(--red-dim);
      border-color: rgba(248,81,73,.25);
    }

    .status-badge {
      font-size: .72rem;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 20px;
      letter-spacing: .5px;
    }
    .status-badge.online  { background: var(--green-dim); color: var(--green); border: 1px solid rgba(63,185,80,.3); }
    .status-badge.offline { background: var(--red-dim);   color: var(--red);   border: 1px solid rgba(248,81,73,.3); }

    .card-name {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.05rem;
      font-weight: 600;
      margin-bottom: 3px;
    }
    .card-location {
      font-size: .8rem;
      color: var(--muted);
    }

    /* ── Slot progress bar ────────────────────────────── */
    .slot-info {
      margin-top: 16px;
    }
    .slot-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }
    .slot-label { font-size: .8rem; color: var(--muted); }
    .slot-count {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.4rem;
      font-weight: 700;
      color: var(--green);
    }
    .slot-total { font-size: .8rem; color: var(--muted); }
    .slot-count.zero { color: var(--red); }

    .progress-track {
      height: 6px;
      background: var(--surface2);
      border-radius: 99px;
      overflow: hidden;
    }
    .progress-fill {
      height: 100%;
      border-radius: 99px;
      background: linear-gradient(90deg, #238636, #3fb950);
      transition: width .6s ease;
    }
    .progress-fill.low  { background: linear-gradient(90deg, #b45309, var(--yellow)); }
    .progress-fill.zero { background: var(--red); }

    /* ── Action panel ─────────────────────────────────── */
    .action-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 28px;
      margin-bottom: 28px;
      text-align: center;
    }

    .action-title {
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 6px;
    }
    .action-desc {
      color: var(--muted);
      font-size: .88rem;
      margin-bottom: 22px;
    }

    /* ── Main CTA button ──────────────────────────────── */
    .btn-request {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      background: linear-gradient(135deg, #238636, #2ea043);
      color: #fff;
      border: none;
      border-radius: 10px;
      padding: 14px 32px;
      font-family: 'Space Grotesk', sans-serif;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: transform .15s ease, box-shadow .15s ease, filter .15s ease;
      box-shadow: 0 4px 20px rgba(35,134,54,.4);
      letter-spacing: .3px;
    }
    .btn-request:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 28px rgba(35,134,54,.55);
      filter: brightness(1.1);
    }
    .btn-request:active:not(:disabled) { transform: translateY(0); }
    .btn-request:disabled {
      background: var(--surface2);
      color: var(--muted);
      cursor: not-allowed;
      box-shadow: none;
    }

    /* ── Result box ───────────────────────────────────── */
    .result-box {
      margin-top: 20px;
      padding: 14px 20px;
      border-radius: 10px;
      font-weight: 500;
      font-size: .92rem;
      display: none;
      animation: fadeIn .3s ease;
      text-align: left;
    }
    .result-box.success {
      background: var(--green-dim);
      border: 1px solid rgba(63,185,80,.3);
      color: var(--green);
      display: block;
    }
    .result-box.error {
      background: var(--red-dim);
      border: 1px solid rgba(248,81,73,.3);
      color: var(--red);
      display: block;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* ── Demo controls ────────────────────────────────── */
    .demo-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 22px;
    }
    .demo-title {
      font-size: .85rem;
      font-weight: 600;
      color: var(--muted);
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .demo-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .btn-release {
      background: var(--surface2);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 16px;
      font-size: .82rem;
      font-family: 'DM Sans', sans-serif;
      cursor: pointer;
      transition: background .15s, border-color .15s, transform .15s;
    }
    .btn-release:hover {
      background: var(--blue-dim);
      border-color: var(--blue);
      color: var(--blue);
      transform: translateY(-1px);
    }

    /* ── Footer ───────────────────────────────────────── */
    footer {
      text-align: center;
      margin-top: 48px;
      color: var(--muted);
      font-size: .78rem;
    }

    /* ── Loading skeleton ─────────────────────────────── */
    .skeleton {
      background: linear-gradient(90deg, var(--surface) 25%, var(--surface2) 50%, var(--surface) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: 6px;
      height: 14px;
    }
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  </style>
</head>
<body>

<div class="container">

  <!-- ── Header ──────────────────────────────────────── -->
  <header>
    <div class="logo-row">
      <div class="logo-icon">⚡</div>
      <h1>EV Charging Dashboard</h1>
    </div>
    <p class="subtitle">Distributed slot allocation system — real-time station monitoring</p>
    <div class="net-bar">
      <div class="pulse" id="netPulse"></div>
      <span id="netStatus">Connecting to network…</span>
    </div>
  </header>

  <!-- ── Stations grid ───────────────────────────────── -->
  <p class="section-label">Charging Stations</p>
  <div class="stations-grid" id="stationsGrid">
    <!-- Populated by JS -->
    <div class="card"><div class="skeleton" style="width:60%;margin-bottom:10px"></div><div class="skeleton" style="width:40%"></div></div>
    <div class="card"><div class="skeleton" style="width:60%;margin-bottom:10px"></div><div class="skeleton" style="width:40%"></div></div>
    <div class="card"><div class="skeleton" style="width:60%;margin-bottom:10px"></div><div class="skeleton" style="width:40%"></div></div>
  </div>

  <!-- ── Allocation action ────────────────────────────── -->
  <div class="action-panel">
    <div class="action-title">⚡ Request a Charging Slot</div>
    <p class="action-desc">The allocator will find the best available station and book a slot for you automatically.</p>
    <button class="btn-request" id="btnRequest" onclick="requestSlot()">
      <span>🔌</span> Request Charging Slot
    </button>
    <div class="result-box" id="resultBox"></div>
  </div>

  <!-- ── Demo: release slots ─────────────────────────── -->
  <div class="demo-panel">
    <div class="demo-title">
      🧪 Demo Controls
      <span style="font-weight:400;color:var(--muted)">— simulate a car leaving to free up a slot</span>
    </div>
    <div class="demo-buttons">
      <button class="btn-release" onclick="releaseSlot('station_1')">Release slot at Alpha</button>
      <button class="btn-release" onclick="releaseSlot('station_2')">Release slot at Beta</button>
      <button class="btn-release" onclick="releaseSlot('station_3')">Release slot at Gamma</button>
    </div>
  </div>

</div>

<footer>EV Charging System · Distributed Architecture Demo · Built with Flask</footer>

<script>
  /* ── Fetch + render all stations ─────────────────── */
  async function loadStations() {
    try {
      const res = await fetch('/api/stations');
      const stations = await res.json();

      const grid = document.getElementById('stationsGrid');
      grid.innerHTML = '';  // Clear skeleton loaders

      let onlineCount = 0;
      stations.forEach(s => {
        if (s.online) onlineCount++;
        grid.innerHTML += buildCard(s);
      });

      // Update network status bar
      const netEl = document.getElementById('netStatus');
      const pulse  = document.getElementById('netPulse');
      netEl.textContent = `${onlineCount} of ${stations.length} stations online`;
      pulse.style.background = onlineCount > 0 ? 'var(--green)' : 'var(--red)';

    } catch (err) {
      document.getElementById('netStatus').textContent = 'Allocator unreachable';
      document.getElementById('netPulse').style.background = 'var(--red)';
    }
  }

  /* ── Build HTML for one station card ─────────────── */
  function buildCard(s) {
    const pct   = s.total_slots > 0 ? (s.available_slots / s.total_slots) * 100 : 0;
    const fill  = pct === 0 ? 'zero' : pct <= 33 ? 'low' : '';
    const count = s.online ? `<span class="slot-count ${s.available_slots === 0 ? 'zero' : ''}">${s.available_slots}</span>` : '<span class="slot-count zero">—</span>';
    const icons = ['⚡','🔋','🔌'];
    const icon  = icons[parseInt(s.id?.slice(-1) || '1') - 1] || '⚡';

    return `
      <div class="card ${s.online ? '' : 'offline'}">
        <div class="card-header">
          <div class="card-icon">${icon}</div>
          <span class="status-badge ${s.online ? 'online' : 'offline'}">${s.online ? 'ONLINE' : 'OFFLINE'}</span>
        </div>
        <div class="card-name">${s.name}</div>
        <div class="card-location">📍 ${s.location}</div>
        <div class="slot-info">
          <div class="slot-row">
            <span class="slot-label">Available slots</span>
            <div style="display:flex;align-items:baseline;gap:4px">
              ${count}
              <span class="slot-total">/ ${s.total_slots}</span>
            </div>
          </div>
          <div class="progress-track">
            <div class="progress-fill ${fill}" style="width:${pct}%"></div>
          </div>
        </div>
      </div>`;
  }

  /* ── Request a slot from the allocator ───────────── */
  async function requestSlot() {
    const btn = document.getElementById('btnRequest');
    const box = document.getElementById('resultBox');

    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Allocating…';
    box.className = 'result-box';  // hide

    try {
      const res  = await fetch('/api/request-slot', { method: 'POST' });
      const data = await res.json();

      box.textContent  = data.message;
      box.className    = `result-box ${data.success ? 'success' : 'error'}`;

      if (data.success) loadStations();  // Refresh slot counts

    } catch (err) {
      box.textContent = '❌ Could not reach the allocator server.';
      box.className   = 'result-box error';
    }

    btn.disabled = false;
    btn.innerHTML = '<span>🔌</span> Request Charging Slot';
  }

  /* ── Release a slot (demo helper) ────────────────── */
  async function releaseSlot(stationId) {
    try {
      await fetch(`/api/release-slot/${stationId}`, { method: 'POST' });
      loadStations();
    } catch (err) {
      console.warn('Release failed:', err);
    }
  }

  /* ── Boot: load stations, then refresh every 5s ──── */
  loadStations();
  setInterval(loadStations, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def dashboard():
    """Serve the main dashboard page."""
    return render_template_string(DASHBOARD_HTML)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🎯 Central Allocator running on http://localhost:5000")
    print("   Open http://localhost:5000 in your browser")
    app.run(port=5000, debug=True)
