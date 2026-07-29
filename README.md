# SunClock 🌅

SunClock helps people time their light exposure for better sleep. Enter any city and it shows today's sunrise, sunset, and solar noon, then translates that into practical sleep hygiene guidance: when to get morning light, when to start winding down, and a suggested bedtime. It also includes a bedtime calculator based on full 90-minute sleep cycles rather than a flat "8 hours."

## Links
- [web01](http://100.53.87.87/)
- [web02](http://3.85.107.160/)
- [lb01](http://100.54.239.57/)
- [Demo Video]()

![Web Application screenshot](<sunclock-sleep.jpg>)

## 📋 Table of Contents

- [Features](#-features)
- [Purpose and Value](#-purpose-and-value)
- [Technologies Used](#-technologies-used)
- [API Integration](#-api-integration)
- [Installation Guide](#-installation-guide)
- [Deployment Guide](#-deployment-guide)
- [Usage Instructions](#-usage-instructions)
- [Project Structure](#-project-structure)
- [Challenges and Solutions](#-challenges-and-solutions)
- [Credits and Attribution](#-credits-and-attribution)
- [License](#-license)

---

## ✨ Features

### Core Functionality
- **Live light-time lookup**: sunrise, sunset, and solar noon for any city
- **Personalized sleep guidance**: generated daily from that city's real light times, not static advice
- **Bedtime calculator**: enter a wake-up time, get back bedtime options based on complete 90-minute sleep cycles

### User Interaction Features
- **Comparison list**: save multiple cities, then **filter** by name and **sort** by sunrise time, day length, or name
- **Remove** any saved city from the comparison list at any time
- **Persistent sessions**: saved cities stay in the comparison list via browser local storage
- **Clear error handling**: human-readable messages when a city can't be found, the API is down, or a rate limit is hit

---

## 🎯 Purpose and Value

Light exposure timing is one of the strongest, most evidence-backed levers for regulating the body's sleep-wake cycle. SunClock turns that principle into a genuinely useful tool for:

1. **Shift workers** adjusting their sleep schedule around irregular hours
2. **Travelers** trying to get ahead of jet lag across time zones
3. **New parents** rebuilding a disrupted sleep routine
4. **Anyone** trying to fix an inconsistent sleep pattern

### Why It's Valuable
It doesn't just display sunrise/sunset data — it converts that data into a concrete daily action plan (when to seek morning light, when to dim evening light, when to sleep), which is what makes it more than a novelty lookup tool.

---

## 🛠 Technologies Used

### Backend
- **Python 3 + Flask**: core application and API proxy, so the RapidAPI key never reaches the browser
- **Gunicorn**: production WSGI server

### Frontend
- **HTML5, CSS3, vanilla JavaScript**: no framework overhead

### Infrastructure
- **Nginx**: reverse proxy in front of Gunicorn on each web server
- **HAProxy**: round-robin load balancing between web01 and web02
- **Systemd**: keeps the Gunicorn service running and auto-restarting

---

## 🔌 API Integration

### Sunrise Sunset Times API
**Provider**: [Macca895 on RapidAPI](https://rapidapi.com/Macca895/api/sunrise-sunset-times)

- Returns sunrise, sunset, and solar noon for a given latitude, longitude, and date
- All credit for this data goes to its creator on RapidAPI

### Open-Meteo Geocoding API
**Provider**: [Open-Meteo](https://open-meteo.com/en/docs/geocoding-api) — free, no API key required

- Converts a city name into latitude/longitude/timezone before the sun-time lookup runs

### Security Measures
- API key stored only in `.env`, excluded from version control via `.gitignore`
- The frontend never talks to either external API directly — every request is proxied through the Flask backend
- Secure transmission via HTTPS to the upstream APIs

---

## 📦 Installation Guide

### Prerequisites
- Python 3.8+
- pip
- Git

### 1. Get an API key
1. Create a free account at [rapidapi.com](https://rapidapi.com)
2. Subscribe to the [Sunrise Sunset Times API](https://rapidapi.com/Macca895/api/sunrise-sunset-times)
3. RAPIDAPI_KEY=2bd6b0869fmshff7cad946447086p16f798jsn92e13d7b4ad8

### 2. Clone and set up
```bash
git clone https://github.com/Michelle493/SunClock.git
cd SunClock

python3 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

### 3. Add your API credentials
Create a `.env` file in the project root:
```env
RAPIDAPI_KEY=your_rapidapi_key_here
RAPIDAPI_HOST=sunrise-sunset-times.p.rapidapi.com
RAPIDAPI_URL=https://sunrise-sunset-times.p.rapidapi.com/getSunTimes
```

### 4. Run it
```bash
python app.py
```
Visit **http://localhost:5000**, search a city, add a few to the comparison list, and try the bedtime calculator.

---

## 🚀 Deployment Guide

The app runs identically on both web servers behind Gunicorn + Nginx, with HAProxy distributing traffic between them.

web-01  App server  100.53.87.87
web-02  App server  3.85.107.160
lb-01 Load balancer 100.54.239.57


### Part 1: web-01 and web-02 (identical setup on both)

**Step 1 — Install system dependencies**
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx git
```

**Step 2 — Clone and configure**
```bash
git clone https://github.com/Michelle493/SunClock.git sunclock
cd sunclock
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env    # paste RAPIDAPI_KEY, RAPIDAPI_HOST, RAPIDAPI_URL
deactivate
```

**Step 3 — Gunicorn as a systemd service** (`/etc/systemd/system/sunclock.service`):
```ini
[Unit]
Description=SunClock Flask app
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/sunclock
EnvironmentFile=/home/ubuntu/sunclock/.env
ExecStart=/home/ubuntu/sunclock/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sunclock
```

**Step 4 — Nginx as a reverse proxy** (`/etc/nginx/sites-available/sunclock`):
```nginx
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/sunclock /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Verify locally on each server: `curl http://localhost` should return the SunClock HTML.

### Part 2: lb-01 (HAProxy load balancer)

```bash
sudo apt update
sudo apt install -y haproxy
```

Add to `/etc/haproxy/haproxy.cfg`:
```cfg
frontend sunclock_frontend
    bind *:80
    mode http
    default_backend sunclock_backend

backend sunclock_backend
    mode http
    balance roundrobin
    option httpchk GET /
    http-check expect status 200
    server web01 100.53.87.87:80 check
    server web02 3.85.107.160:80 check

listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
```
```bash
sudo haproxy -c -f /etc/haproxy/haproxy.cfg
sudo systemctl restart haproxy
```

### Verification

1. **Test individual servers**
   - Visit `http://100.53.87.87/` — should show SunClock
   - Visit `http://3.85.107.160/` — should show SunClock
2. **Test the load balancer**
   - Visit `http://100.54.239.57/` repeatedly — traffic should distribute round-robin between web-01 and web-02
   - Confirmed via HAProxy's built-in stats page at `http://100.54.239.57:8404/stats`, which shows live request counts and "UP" health-check status for both backend servers

---

## 📖 Usage Instructions

1. **Search a city** — enter its name to get today's sunrise, sunset, and solar noon
2. **Read your personalized guidance** — when to get morning light, when to start dimming evening light, and a suggested wind-down time
3. **Use the bedtime calculator** — enter a wake-up time to get bedtime options based on complete 90-minute sleep cycles
4. **Build a comparison list** — save multiple cities, then filter by name or sort by sunrise time, day length, or name
5. **Remove a city** any time — your list persists across sessions via local storage

---

## 📁 Project Structure

```
SunClock/
├── app.py                 # Flask backend / API proxy
├── requirements.txt
├── .env                    # RAPIDAPI_KEY / HOST / URL — never committed
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/script.js
```

---

## 🧩 Challenges and Solutions

### Challenge 1: Undocumented API parameters
**Problem**: the RapidAPI listing page didn't expose parameter names in a way that was easy to inspect ahead of time.
**Solution**: used RapidAPI's built-in "Endpoints" code-snippet generator, which produced a working example request with the real parameter names (`latitude`, `longitude`, `date`, `timeZoneId`).

### Challenge 2: Non-standard timestamp format
**Problem**: the API returns timestamps in a Java-style zoned format (e.g. `2024-01-15T07:18:41-05:00[America/New_York]`), which Python's standard `datetime.fromisoformat()` cannot parse directly.
**Solution**: strip the trailing `[Region/City]` portion before parsing.

### Challenge 3: Missing day-length field
**Problem**: the API doesn't return day length directly.
**Solution**: calculate it as the difference between sunset and sunrise.

### Challenge 4: Keeping the API key secret
**Problem**: avoid any exposure of the key to the browser.
**Solution**: the frontend never talks to the external API directly — all requests go through the Flask backend, which reads the key from an environment variable excluded from version control via `.gitignore`.

### Challenge 5: API downtime, rate limits, and bad responses
**Problem**: the app needed to stay usable even when the external API misbehaves.
**Solution**: the backend catches timeouts, connection errors, invalid keys (401/403), rate limits (429), and malformed JSON, returning a clear, human-readable message instead of crashing.

### Challenge 6: Static/template folder placement
**Problem**: early in development, the `static` folder was accidentally nested inside `templates`, causing all CSS/JS to 404.
**Solution**: Flask requires `static/` and `templates/` to be sibling folders at the project root.

### Challenge 7: Deployment typo
**Problem**: a small typo during deployment went unnoticed and caused some avoidable troubleshooting.
**Solution**: resolved by carefully re-checking file and path spellings.

---

## 🙏 Credits and Attribution

### APIs
- **Sunrise Sunset Times API** — [Macca895 on RapidAPI](https://rapidapi.com/Macca895/api/sunrise-sunset-times) — sun time data
- **Open-Meteo Geocoding API** — [Open-Meteo](https://open-meteo.com/en/docs/geocoding-api) — city name → coordinates

### Libraries and Frameworks
- **Flask** — web framework by Pallets Projects
- **Gunicorn** — WSGI server
- **HAProxy** — load balancer by Willy Tarreau
- **Google Fonts** — Fraunces, Inter, IBM Plex Mono

---

## 📝 License

Built for educational purposes as part of a coursework assignment.

- Educational use: ✅ Allowed
- Commercial use: ❌ Not permitted without authorization
- Modification: ✅ Allowed for learning purposes

Sun time data and geocoding are provided by the third-party APIs credited above; all underlying astronomical data belongs to those services and is governed by their respective terms of service.