# station1.py — EV Charging Station Node 1
# This simulates a real charging station running as its own service.
# It keeps track of available slots in memory (no database needed).

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the allocator

# ── In-memory station data ────────────────────────────────────────────────────
station_data = {
    "id": "station_1",
    "name": "Station Alpha",
    "location": "North Campus",
    "total_slots": 6,
    "available_slots": 6,
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
    print("🔌 Station Alpha running on http://localhost:5001")
    app.run(port=5001, debug=True)
