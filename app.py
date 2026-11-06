
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

# Local practice project ke liye secret key
app.config["SECRET_KEY"] = "change-this-practice-secret-key"

# Rate limiter configuration
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://"
)

# Database project folder mein banegi
BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "users.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


# Rate limit exceed hone par friendly message
@app.errorhandler(429)
def ratelimit_handler(e):
    flash(
        "Bahut zyada login attempts ho gaye. "
        "Kripya 1 minute wait karke dobara try karo."
    )
    return render_template("login.html"), 429


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email aur password dono bharna zaroori hai.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password kam se kam 8 characters ka hona chahiye.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        try:
            with get_db() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (email, password_hash)
                    VALUES (?, ?)
                    """,
                    (email, password_hash)
                )
                user_id = cursor.lastrowid

            session.clear()
            session["user_id"] = user_id
            session["email"] = email

            return redirect(url_for("dashboard"))

        except sqlite3.IntegrityError:
            flash("Ye email pehle se registered hai.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                """
                SELECT id, email, password_hash
                FROM users
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["email"] = user["email"]

            return redirect(url_for("dashboard"))

        flash("Email ya password galat hai.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        flash("Dashboard dekhne ke liye login karo.")
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Tum successfully logout ho gaye.")
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
