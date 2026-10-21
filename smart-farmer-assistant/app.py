
from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

CROP_TIPS = {
    "Rice": [
        "Maintain suitable soil moisture, especially during important growth stages.",
        "Monitor weeds and inspect plants regularly for pests.",
        "Avoid excessive fertilizer and follow local agricultural guidance."
    ],
    "Wheat": [
        "Provide irrigation according to the crop's growth stage and rainfall.",
        "Check plants regularly for rust and other diseases.",
        "Use balanced fertilizer based on soil-test results."
    ],
    "Tomato": [
        "Water near the roots and avoid keeping leaves continuously wet.",
        "Provide support to plants and inspect for pests regularly.",
        "Ensure good drainage to reduce the risk of root diseases."
    ],
    "Maize": [
        "Ensure adequate moisture during flowering and grain formation.",
        "Control weeds early in the growing season.",
        "Inspect plants for fall armyworm and other pests."
    ],
    "Coconut": [
        "Maintain drainage and provide water during dry periods.",
        "Use organic matter and balanced nutrients as locally recommended.",
        "Inspect palms regularly for pest damage."
    ],
    "Sugarcane": [
        "Maintain suitable moisture without waterlogging the field.",
        "Control weeds during early crop growth.",
        "Monitor for stem borers and other common pests."
    ]
}


@app.route("/")
def home():
    return render_template("index.html")


def read_farm_details():
    data = request.get_json(silent=True) or {}

    crop = str(data.get("crop", "Rice")).strip()
    location = str(data.get("location", "")).strip()
    soil = str(data.get("soil", "")).strip()
    moisture = str(data.get("moisture", "")).strip()

    if not location:
        return None, (jsonify({"error": "Please enter your farm location."}), 400)

    if crop not in CROP_TIPS:
        return None, (jsonify({"error": "Please choose a valid crop."}), 400)

    return {
        "crop": crop,
        "location": location,
        "soil": soil,
        "moisture": moisture
    }, None


@app.route("/api/farm-advice", methods=["POST"])
@app.route("/api/recommendations", methods=["POST"])
def farm_advice():
    farm, error = read_farm_details()

    if error:
        return error

    tips = list(CROP_TIPS[farm["crop"]])

    if farm["soil"] == "Clay":
        tips.append("Check drainage carefully because clay soil can retain water.")
    elif farm["soil"] == "Sandy":
        tips.append("Check soil moisture frequently because sandy soil drains quickly.")
    elif farm["soil"] == "Loamy":
        tips.append("Maintain organic matter and avoid overwatering.")

    if farm["moisture"] == "Dry":
        tips.append("Check whether irrigation is needed before the crop becomes stressed.")
    elif farm["moisture"] == "Wet":
        tips.append("Check for standing water and ensure adequate field drainage.")

    return jsonify({
        "message": "Farming recommendations generated successfully!",
        "crop": farm["crop"],
        "farm": farm,
        "recommendations": tips,
        "note": "General guidance only. Confirm crop-specific decisions with local agricultural experts."
    })


@app.route("/api/weather", methods=["POST"])
def get_weather():
    data = request.get_json(silent=True) or {}
    location = str(data.get("location", "")).strip()

    if not location:
        return jsonify({"error": "Please enter your farm location."}), 400

    try:
        geo_response = requests.get(
            GEOCODING_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=15
        )
        geo_response.raise_for_status()
        places = geo_response.json().get("results", [])

        if not places:
            return jsonify({
                "error": "Location not found. Try a nearby town or city name."
            }), 404

        place = places[0]
        latitude = place["latitude"]
        longitude = place["longitude"]

        weather_response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,"
                    "precipitation,wind_speed_10m"
                ),
                "timezone": "auto"
            },
            timeout=15
        )
        weather_response.raise_for_status()

        current = weather_response.json().get("current", {})

        if not current:
            return jsonify({"error": "Current weather data is unavailable."}), 502

        return jsonify({
            "message": "Weather retrieved successfully!",
            "location": f'{place["name"]}, {place.get("country", "")}',
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "time": current.get("time"),
            "units": weather_response.json().get("current_units", {})
        })

    except requests.RequestException:
        return jsonify({
            "error": "Could not contact the weather service. Check your internet connection and try again."
        }), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)
