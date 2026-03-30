from flask import Flask, render_template, request, jsonify
from fetcher import OpenF1Fetcher
from model import compute_probabilities
import threading
import time

app = Flask(__name__)

race_data={
    "fetcher": None,
    "state": None,
    "probs": {},
    "active":False
}

def data_worker():
    """background thread that fetches data every 5 seconds with out blocking the website"""
    while True:
        if race_data["fetcher"]:
            try:
                state = race_data["fetcher"].fetch()
                probs = compute_probabilities(state)
                race_data["state"] = state
                race_data["probs"] = probs
                race_data["active"] = True
            except Exception as e:
                print(f"Error in data worker: {e}")
        time.sleep(5)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/init", methods=["POST"])
def init_race():
    config = request.json

    race_data["fetcher"] = OpenF1Fetcher(
        session_key=config["session_key"],
        total_laps=config["total_laps"]
    )
    return jsonify({"status": "started"})

@app.route("/state")
def get_api_state():
    state = race_data["state"]
    probs = race_data["probs"]
    
    if not state:
        return jsonify({"waiting": True}), 202
    
    drivers = []
    for d in state.drivers.values():
        if d.position < 90:
            drivers.append({
                "number": d.driver_number,
                "name": d.name,
                "position": d.position,
                "team": d.team,
                "color": d.team_color,
                "tyre_compound": d.tyre_compound,
                "tyre_age": d.tyre_age,
                "gap_to_leader": d.gap_to_leader,
                "lap_delta": d.lap_delta,
                "probability": probs.get(d.driver_number, 0),
            })
    drivers.sort(key=lambda x: x["probability"], reverse=True)
    return jsonify({
        "lap": state.current_lap,
        "total_laps": state.total_laps,
        "sc": state.safety_car_active,
        "vsc": state.virtual_safety_car_active,
        "red": state.red_flag,
        "drivers": drivers
    })

if __name__ == "__main__":
    threading.Thread(target=data_worker, daemon=True).start()
    app.run(debug=True, port=5000)