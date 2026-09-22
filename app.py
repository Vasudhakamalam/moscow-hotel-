import os
import resend
import sqlite3
import json
import urllib.request
import urllib.error
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "moscow_hotel.db"

# Demo defaults. For deployment, set ADMIN_USERNAME, ADMIN_PASSWORD and SECRET_KEY
# as environment variables on your hosting platform.
def send_booking_email(guest_name, guest_email, room_name, check_in, check_out, guests):
    """Send an automatic booking confirmation email using Resend."""

    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        print("RESEND_API_KEY is not configured.")
        return

    resend.api_key = api_key

    params = {
        "from": "Moscow Hotel <onboarding@resend.dev>",
        "to": [guest_email],
        "subject": f"Welcome to Moscow Hotel, {guest_name}!",
        "html": f"""
        <h2>Welcome to Moscow Hotel, {guest_name}!</h2>

        <p>
            Thank you for booking your stay with
            <strong>Moscow Hotel, Madurai</strong>.
        </p>

        <h3>Your Booking Details</h3>

        <p><strong>Room:</strong> {room_name}</p>
        <p><strong>Check-in:</strong> {check_in}</p>
        <p><strong>Check-out:</strong> {check_out}</p>
        <p><strong>Guests:</strong> {guests}</p>

        <p>
            We are happy to welcome you and look forward to your stay.
        </p>

        <p>
            Warm regards,<br>
            <strong>Moscow Hotel Team</strong>
        </p>
        """
    }

    try:
        email = resend.Emails.send(params)
        print("Booking email sent successfully:", email)

    except Exception as error:
        print("Resend email error:", error)

ROOMS = [
    {"id": 1, "name": "Deluxe Room", "price": 4500, "image": "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1200&q=80", "description": "Elegant room with a king bed, workspace and city view."},
    {"id": 2, "name": "Executive Suite", "price": 7500, "image": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80", "description": "Spacious suite with a separate living area and premium amenities."},
    {"id": 3, "name": "Family Room", "price": 6000, "image": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80", "description": "Comfortable family accommodation with flexible sleeping arrangements."},
]

MENU = [
    {"category": "Starters", "name": "Moscow Signature Soup", "description": "Rich seasonal soup with herbs and toasted bread.", "price": 280},
    {"category": "Starters", "name": "Crispy Paneer Bites", "description": "Golden paneer with house dipping sauce.", "price": 320},
    {"category": "Main Course", "name": "Moscow Special Biryani", "description": "Aromatic basmati rice, spices and your choice of protein.", "price": 520},
    {"category": "Main Course", "name": "Creamy Alfredo Pasta", "description": "Silky parmesan sauce, mushrooms and fresh herbs.", "price": 460},
    {"category": "Main Course", "name": "Grilled Herb Chicken", "description": "Tender chicken with vegetables and roasted potatoes.", "price": 580},
    {"category": "Desserts", "name": "Chocolate Lava Cake", "description": "Warm chocolate cake with a molten center.", "price": 290},
    {"category": "Desserts", "name": "Classic Cheesecake", "description": "Creamy cheesecake with berry compote.", "price": 260},
    {"category": "Beverages", "name": "Fresh Lime Cooler", "description": "Refreshing lime, mint and sparkling water.", "price": 180},
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guest_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            room_name TEXT NOT NULL,
            check_in TEXT NOT NULL,
            check_out TEXT NOT NULL,
            guests INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in as the hotel administrator.")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/")
def home():
    return render_template("index.html", rooms=ROOMS, menu=MENU)

@app.route("/book", methods=["POST"])
def book():
    guest_name = request.form.get("guest_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    room_name = request.form.get("room_name", "").strip()
    check_in = request.form.get("check_in", "")
    check_out = request.form.get("check_out", "")
    guests_raw = request.form.get("guests", "1")

    try:
        guests = int(guests_raw)
    except ValueError:
        guests = 0

    valid_room = any(room["name"] == room_name for room in ROOMS)

    if not all([guest_name, email, phone, room_name, check_in, check_out]) or guests < 1 or not valid_room:
        flash("Please complete all booking details.")
        return redirect(url_for("home") + "#booking")

    try:
        start = datetime.strptime(check_in, "%Y-%m-%d")
        end = datetime.strptime(check_out, "%Y-%m-%d")
        if end <= start:
            flash("Check-out must be after check-in.")
            return redirect(url_for("home") + "#booking")
    except ValueError:
        flash("Please select valid check-in and check-out dates.")
        return redirect(url_for("home") + "#booking")

    conn = get_db()
    conn.execute(
        """INSERT INTO bookings
        (guest_name, email, phone, room_name, check_in, check_out, guests, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (guest_name, email, phone, room_name, check_in, check_out, guests,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    # Automatically send a personalized welcome email
    send_booking_email(
        guest_name,
        email,
        room_name,
        check_in,
        check_out,
        guests
    )

    flash(f"Booking request received for {room_name}. We will contact you at {email}.")
    return redirect(url_for("home") + "#booking")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin_dashboard"))
        flash("Invalid administrator username or password.")

    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    bookings = conn.execute("SELECT * FROM bookings ORDER BY id DESC").fetchall()
    total = len(bookings)
    today = datetime.now().strftime("%Y-%m-%d")
    checkins_today = conn.execute("SELECT COUNT(*) FROM bookings WHERE check_in = ?", (today,)).fetchone()[0]
    upcoming = conn.execute("SELECT COUNT(*) FROM bookings WHERE check_in >= ?", (today,)).fetchone()[0]
    conn.close()
    return render_template(
        "admin_dashboard.html",
        bookings=bookings,
        total=total,
        checkins_today=checkins_today,
        upcoming=upcoming,
    )

# Backward-compatible route, but now protected.
@app.route("/bookings")
@admin_required
def bookings():
    return redirect(url_for("admin_dashboard"))
init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
