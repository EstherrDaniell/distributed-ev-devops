# station2.py — EV Charging Station Node 2
# Identical structure to station1.py but different data and port.
# In a real distributed system, each of these could run on separate machines.

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ── In-memory station data ────────────────────────────────────────────────────
station_data = {
    "id": "station_2",
    "name": "Station Beta",
    "location": "South Campus",
    "total_slots": 4,
    "available_slots": 2,   # Starts with fewer free slots to show variety
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/status", methods=["GET"])
def get_status():
    """Return current station status and slot availability."""
    return jsonify(station_data)


@app.route("/book", methods=["POST"])
def book_slot():
    """Book one slot. Returns success or error if no slots left."""
    if station_data["available_slots"] > 0:
        station_data["available_slots"] -= 1
        return jsonify({
            "success": True,
            "message": f"Slot booked at {station_data['name']}",
            "remaining_slots": station_data["available_slots"],
        })
    return jsonify({"success": False, "message": "No slots available"}), 400


@app.route("/release", methods=["POST"])
def release_slot():
    """Release a slot (simulate a car leaving)."""
    if station_data["available_slots"] < station_data["total_slots"]:
        station_data["available_slots"] += 1
        return jsonify({
            "success": True,
            "message": "Slot released",
            "remaining_slots": station_data["available_slots"],
        })
    return jsonify({"success": False, "message": "All slots already free"}), 400


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🔌 Station Beta running on http://localhost:5002")
    app.run(port=5002, debug=True)
