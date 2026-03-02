from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import os
import configparser

config = configparser.ConfigParser()
config.read("config.ini")

DATA_FILE = config.get("app", "data_file", fallback="votes.json")
RESET_TOKEN = config.get("app", "reset_token", fallback=os.environ.get("RESET_TOKEN", "tajny-token-2024"))
SECRET_KEY = config.get("app", "secret_key", fallback=os.environ.get("SECRET_KEY", "dev-secret-key"))

app = Flask(__name__)
app.secret_key = SECRET_KEY

QUESTION = "Kolik otevřených záložek je ještě normální?"
OPTIONS = [
    {"id": "a", "label": "a) 1–5, jsem zen mistr"},
    {"id": "b", "label": "b) 6–20, normální člověk"},
    {"id": "c", "label": "c) 21–50, produktivní chaos"},
    {"id": "d", "label": "d) 51–100, mám to pod kontrolou"},
    {"id": "e", "label": "e) 100+, RAM je slabá, ne já"},
]

# --- Pomocné funkce ---
def load_votes():
    if not os.path.exists(DATA_FILE):
        return {opt["id"]: 0 for opt in OPTIONS}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_votes(votes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, ensure_ascii=False, indent=2)

def total_votes(votes):
    return sum(votes.values())

# --- Routes ---
@app.route("/")
def index():
    votes = load_votes()
    voted_flag = session.get("voted", False)
    return render_template("index.html",
                           question=QUESTION,
                           options=OPTIONS,
                           votes=votes,
                           total=total_votes(votes),
                           voted=voted_flag,
                           error=None)

@app.after_request
def add_security_headers(response):
    """
    Přidá bezpečnostní hlavičky pro ochranu aplikace (Hardening).
    """
    # 1. Ochrana proti ClickJackingu
    response.headers['X-Frame-Options'] = 'DENY'
    
    # 2. Ochrana proti Content Type Sniffing (MIME sniffing)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    # 3. Strict-Transport-Security (HSTS) - Vynucení HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    # 4. Content-Security-Policy (CSP)
    # Povolujeme 'self' (vlastní doménu), Google Analytics (skripty, tracking, obrázky) 
    # a inline styly/skripty, které v aplikaci používáš.
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://www.google-analytics.com https://stats.g.doubleclick.net; "
        "img-src 'self' https://www.google-analytics.com https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "object-src 'none';"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response

@app.route("/vote", methods=["POST"])
def vote():
    choice = request.form.get("choice")
    valid_ids = [opt["id"] for opt in OPTIONS]
    votes = load_votes()

    if session.get("voted"):
        return render_template("index.html",
                               question=QUESTION,
                               options=OPTIONS,
                               votes=votes,
                               total=total_votes(votes),
                               voted=True,
                               error="Už jsi hlasoval, další hlas není povolen.")

    if choice not in valid_ids:
        return render_template("index.html",
                               question=QUESTION,
                               options=OPTIONS,
                               votes=votes,
                               total=total_votes(votes),
                               voted=False,
                               error="Vyber prosím platnou možnost.")

    votes[choice] = votes.get(choice, 0) + 1
    save_votes(votes)
    session["voted"] = True

    return render_template("index.html",
                           question=QUESTION,
                           options=OPTIONS,
                           votes=votes,
                           total=total_votes(votes),
                           voted=True,
                           error=None)

@app.route("/results")
def results():
    votes = load_votes()
    return render_template("index.html",
                           question=QUESTION,
                           options=OPTIONS,
                           votes=votes,
                           total=total_votes(votes),
                           voted=None,
                           error=None)


@app.route("/admin")
def admin():
    votes = load_votes()
    return render_template("index.html",
                           question=QUESTION,
                           options=OPTIONS,
                           votes=votes,
                           total=total_votes(votes),
                           voted=None,
                           error=None,
                           show_reset=True)

@app.route("/reset", methods=["POST"])
def reset():
    token = request.form.get("token", "")
    votes = load_votes()

    if token != RESET_TOKEN:
        return render_template("index.html",
                               question=QUESTION,
                               options=OPTIONS,
                               votes=votes,
                               total=total_votes(votes),
                               voted=None,
                               error="Nesprávný reset token.")

    empty = {opt["id"]: 0 for opt in OPTIONS}
    save_votes(empty)
    session.pop("voted", None)
    return redirect(url_for("results"))

@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(debug=True)
