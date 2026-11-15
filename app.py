from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash
from jinja2 import DictLoader
import database as db
import blockchain as bc
import assistant

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
db.init_db()

TEMPLATES = {
    "base.html": """<!doctype html>
<html><head><meta charset="utf-8">
<title>Land Management System</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="/static/style.css">
</head><body>
<nav>
{% if session.user %}
<a href="/records">Land Records</a>
<a href="/register">Register Land</a>
<a href="/map">GIS Map</a>
<a href="/blockchain">Blockchain</a>
<a href="/verify">Verify</a>
<a href="/assistant">Assistant</a>
<a href="/logout">Logout ({{ session.user }})</a>
{% else %}<b>Blockchain and GIS Based Land Management System</b>{% endif %}
</nav>
<div class="box">
{% with messages = get_flashed_messages() %}
{% for m in messages %}<div class="msg">{{ m }}</div>{% endfor %}
{% endwith %}
{% block content %}{% endblock %}
</div></body></html>""",

"login.html": """{% extends "base.html" %}{% block content %}
<h2>Login</h2>
<form method="post" action="/login">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button>Login</button></form>
<h2>Sign up</h2>
<form method="post" action="/signup">
<input name="username" placeholder="Choose a username" required>
<input name="password" type="password" placeholder="Choose a password" required>
<button>Create account</button></form>
{% endblock %}""",

"register.html": """{% extends "base.html" %}{% block content %}
<h2>Land Registration</h2>
<form method="post">
<input name="survey_no" placeholder="Survey Number" required>
<input name="owner" placeholder="Owner Name" required>
<input name="village" placeholder="Village">
<input name="area" type="number" step="any" placeholder="Area (sq ft)">
<input name="lat" type="number" step="any" placeholder="Latitude (e.g. 12.9716)" required>
<input name="lon" type="number" step="any" placeholder="Longitude (e.g. 77.5946)" required>
<button>Register Land</button></form>
{% endblock %}""",

"records.html": """{% extends "base.html" %}{% block content %}
<h2>Land Records</h2>
{% if lands %}
<table><tr><th>Survey No</th><th>Owner</th><th>Village</th><th>Area (sq ft)</th><th>Lat</th><th>Lon</th></tr>
{% for l in lands %}<tr><td>{{ l.survey_no }}</td><td>{{ l.owner }}</td><td>{{ l.village }}</td>
<td>{{ l.area }}</td><td>{{ l.lat }}</td><td>{{ l.lon }}</td></tr>{% endfor %}</table>
{% else %}<p>No land records yet.</p>{% endif %}
{% endblock %}""",

"map.html": """{% extends "base.html" %}{% block content %}
<h2>GIS Map</h2>
<div id="map" style="height:500px"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var lands = {{ lands|tojson }};
var map = L.map('map').setView([12.9716, 77.5946], 7);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  {attribution: '&copy; OpenStreetMap contributors'}).addTo(map);
var markers = [];
lands.forEach(function(l){
  var m = L.marker([l.lat, l.lon]).addTo(map)
   .bindPopup('<b>Survey No: ' + l.survey_no + '</b><br>Owner: ' + l.owner + '<br>Village: ' + l.village + '<br>Area: ' + l.area + ' sq ft');
  markers.push(m);
});
if (markers.length) { map.fitBounds(L.featureGroup(markers).getBounds().pad(0.3)); }
</script>
{% endblock %}""",

"blockchain.html": """{% extends "base.html" %}{% block content %}
<h2>Blockchain Ledger</h2>
<p>Chain status:
{% if valid %}<span class="ok">VALID - no tampering detected</span>
{% else %}<span class="bad">INVALID - records have been tampered with</span>{% endif %}</p>
<table><tr><th>#</th><th>Time</th><th>Transaction</th><th>Hash</th></tr>
{% for b in chain %}<tr><td>{{ b.index }}</td><td>{{ b.timestamp }}</td>
<td>{% if b.data is mapping %}{{ b.data.action }}: Survey {{ b.data.survey_no }}<br>
{{ b.data['from'] }} to {{ b.data.to }}{% else %}{{ b.data }}{% endif %}</td>
<td class="hash">{{ b.hash }}</td></tr>{% endfor %}</table>
{% endblock %}""",

"verify.html": """{% extends "base.html" %}{% block content %}
<h2>Verify Land Record</h2>
<form method="post">
<input name="survey_no" placeholder="Enter Survey Number" required>
<button>Verify</button></form>
{% if searched %}
  {% if land %}
  <h3>Land Details</h3>
  <p>Owner: <b>{{ land.owner }}</b><br>Village: {{ land.village }}<br>Area: {{ land.area }} sq ft<br>
  Location: {{ land.lat }}, {{ land.lon }}</p>
  <p>Blockchain integrity:
  {% if valid %}<span class="ok">VERIFIED</span>{% else %}<span class="bad">TAMPERED</span>{% endif %}</p>
  <h3>Transaction History</h3>
  <table><tr><th>Time</th><th>Action</th><th>From</th><th>To</th></tr>
  {% for b in history %}<tr><td>{{ b.timestamp }}</td><td>{{ b.data.action }}</td>
  <td>{{ b.data['from'] }}</td><td>{{ b.data.to }}</td></tr>{% endfor %}</table>
  {% else %}<p class="bad">No land found with this survey number.</p>{% endif %}
{% endif %}
{% endblock %}""",
}
TEMPLATES["assistant.html"] = """{% extends "base.html" %}{% block content %}
<h2>Land Records Assistant</h2>
<form method="post">
<input name="question" placeholder="e.g. Who owns survey number 101?" required>
<button>Ask</button></form>
{% if answer %}<h3>Answer</h3><p style="white-space:pre-wrap">{{ answer }}</p>{% endif %}
{% endblock %}"""
app.jinja_env.loader = DictLoader(TEMPLATES)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def land_dicts():
    return [{"survey_no": r[0], "owner": r[1], "village": r[2],
             "area": r[3], "lat": r[4], "lon": r[5]} for r in db.get_lands()]


@app.route("/")
def index():
    return redirect("/records" if "user" in session else "/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = db.check_login(request.form["username"], request.form["password"])
        if role:
            session["user"] = request.form["username"]
            session["role"] = role
            return redirect("/records")
        flash("Invalid username or password")
    return render_template("login.html")


@app.route("/signup", methods=["POST"])
def signup():
    if db.register_user(request.form["username"], request.form["password"]):
        flash("Account created. Please log in.")
    else:
        flash("Username already taken")
    return redirect("/login")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if session.get("role") != "admin":
        flash("Only the admin can register land.")
        return redirect("/records")
    if request.method == "POST":
        f = request.form
        ok = db.add_land(f["survey_no"], f["owner"], f["village"],
                         float(f["area"] or 0), float(f["lat"]), float(f["lon"]))
        if ok:
            bc.add_transaction(f["survey_no"], "REGISTER", "-", f["owner"])
            flash("Land registered and recorded on the blockchain.")
            return redirect("/records")
        flash("This survey number already exists.")
    return render_template("register.html")


@app.route("/records")
@login_required
def records():
    return render_template("records.html", lands=land_dicts())


@app.route("/map")
@login_required
def gis_map():
    return render_template("map.html", lands=land_dicts())


@app.route("/blockchain")
@login_required
def blockchain_page():
    return render_template("blockchain.html", chain=bc.load_chain(),
                           valid=bc.is_chain_valid())


@app.route("/verify", methods=["GET", "POST"])
@login_required
def verify():
    land = history = None
    searched = False
    if request.method == "POST":
        searched = True
        sno = request.form["survey_no"].strip()
        land = next((l for l in land_dicts() if l["survey_no"] == sno), None)
        history = bc.get_history(sno)
    return render_template("verify.html", searched=searched, land=land,
                           history=history, valid=bc.is_chain_valid())



@app.route("/assistant", methods=["GET", "POST"])
@login_required
def assistant_page():
    answer = None
    if request.method == "POST":
        answer = assistant.ask(request.form["question"])
    return render_template("assistant.html", answer=answer)
if __name__ == "__main__":
    app.run(debug=True)