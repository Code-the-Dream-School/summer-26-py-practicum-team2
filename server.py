from flask import Flask, jsonify, request
from flask_cors import CORS

import random
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

SAMPLE_CITIES = [
    {
        "id": "chicago-us",
        "cityName": "Chicago, US",
        "aqi": 2,
        "trend": [
            {"time": "6h", "aqi": 2},
            {"time": "9h", "aqi": 2},
            {"time": "12h", "aqi": 3},
            {"time": "15h", "aqi": 3},
            {"time": "18h", "aqi": 2},
            {"time": "21h", "aqi": 1},
        ],
    },
    {
        "id": "miami-us",
        "cityName": "Miami, US",
        "aqi": 1,
        "trend": [
            {"time": "6h", "aqi": 1},
            {"time": "9h", "aqi": 1},
            {"time": "12h", "aqi": 2},
            {"time": "15h", "aqi": 1},
            {"time": "18h", "aqi": 1},
            {"time": "21h", "aqi": 1},
        ],
    },
]

def generate_daily_history(base_aqi: int, days: int = 14) -> list[dict]:
    """Generate synthetic daily AQI history for aggregation demos."""
    today = datetime.now()
    history = []
    for i in range(days):
        date = (today - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        # small random variation around the city's typical AQI
        aqi = max(1, min(5, base_aqi + random.choice([-1, 0, 0, 0, 1])))
        history.append({"date": date, "aqi": aqi})
    return history

@app.route("/api/cities")
def get_cities():
    return jsonify([{"id": c["id"], "cityName": c["cityName"]} for c in SAMPLE_CITIES])


@app.route("/api/cities/<city_id>/trend")
def get_city_trend(city_id):
    city = next((c for c in SAMPLE_CITIES if c["id"] == city_id), None)
    if city is None:
        return jsonify({"error": "city not found"}), 404
    return jsonify(city)

@app.route("/api/cities/overview")
def get_cities_overview():
    return jsonify([
        {"id": c["id"], "cityName": c["cityName"], "aqi": c["aqi"]}
        for c in SAMPLE_CITIES
    ])

@app.route("/api/cities/<city_id>/aggregates")
def get_city_aggregates(city_id):
    city = next((c for c in SAMPLE_CITIES if c["id"] == city_id), None)
    if city is None:
        return jsonify({"error": "city not found"}), 404

    period = request.args.get("period", "daily")
    daily_history = generate_daily_history(city["aqi"])

    if period == "weekly":
        # group every 7 days into one bucket, average the AQI
        weekly = []
        for i in range(0, len(daily_history), 7):
            chunk = daily_history[i : i + 7]
            avg_aqi = round(sum(d["aqi"] for d in chunk) / len(chunk), 1)
            weekly.append({"date": f"Week of {chunk[0]['date']}", "aqi": avg_aqi})
        return jsonify(weekly)

    return jsonify(daily_history)

if __name__ == "__main__":
    app.run(port=8000, debug=True)