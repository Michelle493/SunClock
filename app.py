import os
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "sunrise-sunset-times.p.rapidapi.com")
RAPIDAPI_URL = os.getenv("RAPIDAPI_URL", "https://sunrise-sunset-times.p.rapidapi.com/getSunTimes")
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"

_cache = {}
CACHE_TTL = 600


def cache_get(key):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < CACHE_TTL:
        return entry["data"]
    return None


def cache_set(key, data):
    _cache[key] = {"data": data, "ts": time.time()}


def parse_zoned_time(value):
    """Strip the trailing [Region/City] from Java-style zoned timestamps
    (e.g. '2024-01-15T07:18:41-05:00[America/New_York]') so Python can parse it."""
    if not value:
        return None
    clean = value.split("[")[0]
    try:
        return datetime.fromisoformat(clean)
    except ValueError:
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/suntimes")
def suntimes():
    city = request.args.get("city", "").strip()
    if not city:
        return jsonify({"error": "Please enter a city name."}), 400

    cache_key = f"suntimes:{city.lower()}"
    cached = cache_get(cache_key)
    if cached:
        return jsonify(cached)

    try:
        geo_resp = requests.get(GEOCODE_URL, params={"name": city, "count": 1}, timeout=8)
    except requests.exceptions.RequestException:
        return jsonify({"error": "Could not reach the geocoding service. Please try again."}), 502

    if geo_resp.status_code != 200:
        return jsonify({"error": "Geocoding service returned an error."}), 502

    results = geo_resp.json().get("results")
    if not results:
        return jsonify({"error": f"Couldn't find a place called '{city}'. Try a different spelling."}), 404

    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    timezone_id = place.get("timezone", "UTC")
    place_name = f"{place.get('name')}, {place.get('country', '')}".strip(", ")

    if not RAPIDAPI_KEY:
        return jsonify({"error": "Server is missing its API key. Set RAPIDAPI_KEY in .env."}), 500

    headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}
    params = {
        "latitude": lat,
        "longitude": lon,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "timeZoneId": timezone_id,
    }

    try:
        sun_resp = requests.get(RAPIDAPI_URL, headers=headers, params=params, timeout=10)
    except requests.exceptions.Timeout:
        return jsonify({"error": "The sun times API took too long to respond. Try again."}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Could not reach the sun times API: {e}"}), 502

    if sun_resp.status_code == 429:
        return jsonify({"error": "Rate limit reached. Please wait a moment and try again."}), 429
    if sun_resp.status_code in (401, 403):
        return jsonify({"error": "API authentication failed - check your RapidAPI key or subscription."}), 401
    if sun_resp.status_code != 200:
        return jsonify({"error": f"Sun times API returned status {sun_resp.status_code}."}), 502

    try:
        sun_data = sun_resp.json()
    except ValueError:
        return jsonify({"error": "Received an invalid response from the sun times API."}), 502

    sunrise_dt = parse_zoned_time(sun_data.get("sunrise"))
    sunset_dt = parse_zoned_time(sun_data.get("sunset"))
    solar_noon_dt = parse_zoned_time(sun_data.get("solarNoon"))

    day_length = None
    if sunrise_dt and sunset_dt:
        delta = sunset_dt - sunrise_dt
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        day_length = f"{hours}h {minutes}m"

    result = {
        "place": place_name,
        "lat": lat,
        "lon": lon,
        "sunrise": sunrise_dt.isoformat() if sunrise_dt else None,
        "sunset": sunset_dt.isoformat() if sunset_dt else None,
        "solar_noon": solar_noon_dt.isoformat() if solar_noon_dt else None,
        "day_length": day_length,
        "civil_twilight_begin": sun_data.get("civilTwilightMorning"),
        "civil_twilight_end": sun_data.get("civilTwilightEvening"),
        "tips": build_sleep_tips(sunrise_dt, sunset_dt),
    }

    cache_set(cache_key, result)
    return jsonify(result)


def build_sleep_tips(sunrise_dt, sunset_dt):
    if not sunrise_dt or not sunset_dt:
        return ["Couldn't calculate personalized tips for this location."]

    morning_end = sunrise_dt + timedelta(minutes=45)
    winddown_start = sunset_dt - timedelta(hours=1)
    suggested_bedtime = sunset_dt + timedelta(hours=5)

    return [
        f"Get outside for bright light between {sunrise_dt.strftime('%I:%M %p')} and {morning_end.strftime('%I:%M %p')} to anchor your body clock.",
        f"Start dimming lights and avoiding screens from {winddown_start.strftime('%I:%M %p')} onward.",
        f"A reasonable target bedtime tonight is around {suggested_bedtime.strftime('%I:%M %p')}.",
    ]


@app.route("/api/bedtime")
def bedtime_calculator():
    wake_time = request.args.get("wake_time")
    if not wake_time:
        return jsonify({"error": "Provide a wake_time in HH:MM format."}), 400
    try:
        hour, minute = map(int, wake_time.split(":"))
        wake_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        return jsonify({"error": "wake_time must be in HH:MM format, e.g. 06:30."}), 400

    options = []
    for cycles in [6, 5, 4]:
        time_needed = timedelta(hours=1.5 * cycles) + timedelta(minutes=15)
        bedtime = wake_dt - time_needed
        options.append({
            "cycles": cycles,
            "hours_sleep": 1.5 * cycles,
            "bedtime": bedtime.strftime("%I:%M %p"),
        })

    return jsonify({"wake_time": wake_dt.strftime("%I:%M %p"), "options": options})


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)