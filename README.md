# ⚡ Distributed EV Charging Slot Allocation System

A beginner-friendly distributed systems demo built with Python + Flask.

---

## 📁 File Structure

```
ev_charging/
├── station1.py      ← Charging station node (port 5001)
├── station2.py      ← Charging station node (port 5002)
├── station3.py      ← Charging station node (port 5003)
├── allocator.py     ← Central allocator + dashboard (port 5000)
└── requirements.txt
```

---

## 🚀 How to Run

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Open 4 terminal windows and run each file

**Terminal 1 — Station Alpha:**
```bash
python station1.py
```

**Terminal 2 — Station Beta:**
```bash
python station2.py
```

**Terminal 3 — Station Gamma:**
```bash
python station3.py
```

**Terminal 4 — Central Allocator (main dashboard):**
```bash
python allocator.py
```

### Step 3 — Open your browser
Visit: **http://localhost:5000**

---

## 🧪 Testing Fault Tolerance

Stop any station (Ctrl+C in its terminal).  
Refresh the dashboard — that card shows **OFFLINE** in red.  
Click "Request Charging Slot" — the system skips the offline station and allocates from the remaining ones. ✅

---

## 📡 Sample API Responses

**GET http://localhost:5001/status**
```json
{
  "id": "station_1",
  "name": "Station Alpha",
  "location": "North Campus",
  "total_slots": 6,
  "available_slots": 5
}
```

**GET http://localhost:5000/api/stations**
```json
[
  { "id": "station_1", "name": "Station Alpha", "available_slots": 5, "online": true },
  { "id": "station_2", "name": "Station Beta",  "available_slots": 2, "online": true },
  { "id": "station_3", "name": "Station Gamma", "available_slots": 0, "online": false }
]
```

**POST http://localhost:5000/api/request-slot**
```json
{
  "success": true,
  "message": "✅ Slot allocated at Station Alpha (North Campus)",
  "station": "Station Alpha",
  "remaining_slots": 4
}
```

---

## 🏛️ Distributed System Concepts Used

| Concept | How it's implemented |
|---------|---------------------|
| **Distributed nodes** | Each station is a separate Flask process on its own port |
| **Central coordinator** | `allocator.py` is the single point of coordination |
| **REST communication** | Nodes talk via HTTP JSON APIs |
| **Fault tolerance** | `try/except` with a timeout — offline nodes are skipped |
| **Load balancing** | Allocator picks the station with the most free slots |
| **Scalability** | Add a new station by adding one entry to `STATIONS` list |

---

## 💡 How the Allocation Works (Step by Step)

1. User clicks **"Request Charging Slot"** → browser calls `POST /api/request-slot`
2. Allocator contacts every registered station (`GET /status`) with a 2-second timeout
3. Stations that don't respond are marked **offline** — system continues
4. Allocator picks the online station with the **most free slots**
5. Allocator calls `POST /book` on the chosen station
6. Result is returned to the browser and displayed on the dashboard
7. Dashboard auto-refreshes every 5 seconds to show live slot counts
