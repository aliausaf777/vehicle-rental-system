from flask import Flask, render_template, request, redirect, session, flash, url_for
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "elite_auto_secure_key_2025"

# ── Jinja filter ───────────────────────────────────────────────
@app.template_filter('format_inr')
def format_inr(value):
    try:
        return "{:,.0f}".format(float(value))
    except:
        return value

# ── Database ───────────────────────────────────────────────────
DB = {"host": "127.0.0.1", "user": "root", "password": "ausaf", "database": "car_rental"}

def get_db():
    return mysql.connector.connect(**DB)

def logged_in():
    return "user_id" in session

def is_admin():
    return session.get("role") == "admin"

def require_login():
    if not logged_in():
        return redirect("/login")

# ── LOGIN ──────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if logged_in():
        return redirect("/admin" if is_admin() else "/")
    if request.method == "POST":
        email    = request.form["email"].strip()
        password = request.form["password"]
        role     = request.form["role"]
        conn = get_db(); cur = conn.cursor(dictionary=True)

        if role == "customer":
            cur.execute("SELECT * FROM customers WHERE email=%s AND password_hash=%s", (email, password))
            user = cur.fetchone()
            if user:
                session.update({"user_id": user["id"], "name": user["name"], "role": "customer"})
                cur.close(); conn.close()
                flash(f"Welcome back, {user['name']}!")
                return redirect("/")

        elif role == "admin":
            cur.execute("SELECT * FROM admins WHERE username=%s AND password_hash=%s", (email, password))
            admin = cur.fetchone()
            if admin:
                session.update({"user_id": admin["id"], "name": "Admin", "role": "admin"})
                cur.close(); conn.close()
                return redirect("/admin")

        cur.close(); conn.close()
        flash("Invalid credentials. Please try again.")
    return render_template("login.html")


# ── REGISTER ───────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if logged_in():
        return redirect("/")
    if request.method == "POST":
        name     = request.form["name"].strip()
        email    = request.form["email"].strip().lower()
        phone    = request.form.get("phone", "").strip()
        password = request.form["password"]
        confirm  = request.form["confirm"]

        if len(name) < 2:
            flash("Please enter your full name."); return redirect("/register")
        if len(password) < 6:
            flash("Password must be at least 6 characters."); return redirect("/register")
        if password != confirm:
            flash("Passwords do not match."); return redirect("/register")

        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM customers WHERE email=%s", (email,))
        if cur.fetchone():
            flash("An account with this email already exists."); cur.close(); conn.close(); return redirect("/register")

        cur.execute(
            "INSERT INTO customers (name, email, phone, password_hash) VALUES (%s,%s,%s,%s)",
            (name, email, phone, password)
        )
        conn.commit()
        new_id = cur.lastrowid
        cur.close(); conn.close()

        session.update({"user_id": new_id, "name": name, "role": "customer"})
        flash(f"Welcome to Elite Auto, {name}! Start exploring our fleet.")
        return redirect("/")
    return render_template("register.html")


# ── LOGOUT ─────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ── HOME / FLEET ───────────────────────────────────────────────
@app.route("/")
def home():
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT cars.*, categories.name AS category
        FROM cars
        LEFT JOIN categories ON cars.category_id = categories.id
        WHERE cars.available = 1
        ORDER BY cars.id
    """)
    cars = cur.fetchall()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close(); conn.close()
    return render_template("index.html", cars=cars, categories=categories)


# ── CAR DETAIL ─────────────────────────────────────────────────
@app.route("/car/<int:car_id>")
def car_detail(car_id):
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT cars.*, categories.name AS category
        FROM cars LEFT JOIN categories ON cars.category_id = categories.id
        WHERE cars.id=%s
    """, (car_id,))
    car = cur.fetchone()
    if not car:
        cur.close(); conn.close()
        return render_template("404.html"), 404

    # Other available cars (excluding this one)
    cur.execute("""
        SELECT cars.*, categories.name AS category
        FROM cars LEFT JOIN categories ON cars.category_id = categories.id
        WHERE cars.available=1 AND cars.id != %s
        LIMIT 3
    """, (car_id,))
    similar = cur.fetchall()
    cur.close(); conn.close()
    return render_template("car_detail.html", car=car, similar=similar)


# ── BOOK ───────────────────────────────────────────────────────
@app.route("/book/<int:car_id>", methods=["POST"])
def book(car_id):
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM cars WHERE id=%s AND available=1", (car_id,))
    car = cur.fetchone()
    if not car:
        flash("Vehicle not found or unavailable.")
        cur.close(); conn.close()
        return redirect("/")

    pickup = request.form["pickup"]
    ret    = request.form["return"]
    try:
        pickup_dt = datetime.strptime(pickup, "%Y-%m-%d")
        return_dt = datetime.strptime(ret,    "%Y-%m-%d")
    except ValueError:
        flash("Invalid dates."); cur.close(); conn.close(); return redirect(f"/car/{car_id}")

    if return_dt < pickup_dt:
        flash("Return date must be on or after pickup date.")
        cur.close(); conn.close()
        return redirect(f"/car/{car_id}")

    if pickup_dt.date() < datetime.today().date():
        flash("Pickup date cannot be in the past.")
        cur.close(); conn.close()
        return redirect(f"/car/{car_id}")

    days  = (return_dt - pickup_dt).days + 1
    total = days * float(car["price_per_day"])

    cur.execute("""
        INSERT INTO rentals (customer_id, car_id, pickup_date, return_date, total, status)
        VALUES (%s,%s,%s,%s,%s,'pending')
    """, (session["user_id"], car_id, pickup, ret, total))
    conn.commit()
    rental_id = cur.lastrowid
    cur.close(); conn.close()
    return redirect(f"/payment/{rental_id}")


# ── PAYMENT ────────────────────────────────────────────────────
@app.route("/payment/<int:rental_id>")
def payment(rental_id):
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT rentals.*, cars.brand, cars.model, cars.image, cars.price_per_day
        FROM rentals JOIN cars ON rentals.car_id = cars.id
        WHERE rentals.id=%s AND rentals.customer_id=%s AND rentals.status='pending'
    """, (rental_id, session["user_id"]))
    rental = cur.fetchone()
    if not rental:
        flash("Booking not found or already paid.")
        cur.close(); conn.close()
        return redirect("/bookings")
    cur.close(); conn.close()
    return render_template("payment.html", rental=rental, car=rental)


# ── CONFIRM PAYMENT ────────────────────────────────────────────
@app.route("/confirm_payment", methods=["POST"])
def confirm_payment():
    if not logged_in(): return redirect("/login")
    rental_id      = request.form.get("rental_id")
    payment_method = request.form.get("payment_method", "card")

    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        UPDATE rentals SET status='confirmed', payment_method=%s
        WHERE id=%s AND customer_id=%s
    """, (payment_method, rental_id, session["user_id"]))
    conn.commit()
    cur.close(); conn.close()
    return redirect(f"/confirmation/{rental_id}")


# ── BOOKING CONFIRMATION PAGE ─────────────────────────────────
@app.route("/confirmation/<int:rental_id>")
def confirmation(rental_id):
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT rentals.*, cars.brand, cars.model, cars.image, cars.price_per_day
        FROM rentals JOIN cars ON rentals.car_id = cars.id
        WHERE rentals.id=%s AND rentals.customer_id=%s
    """, (rental_id, session["user_id"]))
    rental = cur.fetchone()
    if not rental:
        cur.close(); conn.close(); return redirect("/bookings")
    cur.close(); conn.close()
    return render_template("confirmation.html", rental=rental, car=rental)


# ── MY BOOKINGS ────────────────────────────────────────────────
@app.route("/bookings")
def bookings():
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT rentals.*, cars.brand, cars.model
        FROM rentals JOIN cars ON rentals.car_id = cars.id
        WHERE customer_id=%s ORDER BY rentals.id DESC
    """, (session["user_id"],))
    data = cur.fetchall()
    cur.close(); conn.close()
    return render_template("bookings.html", bookings=data)


# ── CANCEL BOOKING ─────────────────────────────────────────────
@app.route("/cancel_booking/<int:rental_id>")
def cancel_booking(rental_id):
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM rentals WHERE id=%s AND customer_id=%s AND status='pending'",
                (rental_id, session["user_id"]))
    rental = cur.fetchone()
    if not rental:
        flash("Cannot cancel this booking.")
    else:
        cur.execute("UPDATE rentals SET status='cancelled' WHERE id=%s", (rental_id,))
        conn.commit()
        flash("Booking cancelled successfully.")
    cur.close(); conn.close()
    return redirect("/bookings")


# ── PROFILE ────────────────────────────────────────────────────
@app.route("/profile")
def profile():
    if not logged_in(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM customers WHERE id=%s", (session["user_id"],))
    customer = cur.fetchone()

    cur.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(status IN ('confirmed','paid')) AS confirmed,
            SUM(status='completed') AS completed,
            COALESCE(SUM(CASE WHEN status IN ('confirmed','paid','completed') THEN total ELSE 0 END), 0) AS spent
        FROM rentals WHERE customer_id=%s
    """, (session["user_id"],))
    stats = cur.fetchone()

    cur.execute("""
        SELECT rentals.*, cars.brand, cars.model
        FROM rentals JOIN cars ON rentals.car_id=cars.id
        WHERE customer_id=%s ORDER BY rentals.id DESC LIMIT 5
    """, (session["user_id"],))
    recent_bookings = cur.fetchall()
    cur.close(); conn.close()
    return render_template("profile.html", customer=customer, stats=stats, recent_bookings=recent_bookings)


# ── UPDATE PROFILE ─────────────────────────────────────────────
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if not logged_in(): return redirect("/login")
    name  = request.form["name"].strip()
    email = request.form["email"].strip().lower()
    phone = request.form.get("phone", "").strip()

    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE customers SET name=%s, email=%s, phone=%s WHERE id=%s",
                (name, email, phone, session["user_id"]))
    conn.commit()
    session["name"] = name
    cur.close(); conn.close()
    flash("Profile updated successfully.")
    return redirect("/profile")


# ── CHANGE PASSWORD ────────────────────────────────────────────
@app.route("/change_password", methods=["POST"])
def change_password():
    if not logged_in(): return redirect("/login")
    current  = request.form["current"]
    new_pass = request.form["new_pass"]
    confirm  = request.form["confirm"]

    if new_pass != confirm:
        flash("New passwords do not match."); return redirect("/profile")
    if len(new_pass) < 6:
        flash("Password must be at least 6 characters."); return redirect("/profile")

    conn = get_db(); cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM customers WHERE id=%s AND password_hash=%s",
                (session["user_id"], current))
    if not cur.fetchone():
        flash("Current password is incorrect."); cur.close(); conn.close(); return redirect("/profile")

    cur.execute("UPDATE customers SET password_hash=%s WHERE id=%s", (new_pass, session["user_id"]))
    conn.commit(); cur.close(); conn.close()
    flash("Password changed successfully.")
    return redirect("/profile")


# ── ADMIN DASHBOARD ────────────────────────────────────────────
@app.route("/admin")
def admin():
    if not is_admin(): return redirect("/login")
    conn = get_db(); cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT cars.*, categories.name AS category
        FROM cars LEFT JOIN categories ON cars.category_id=categories.id
        ORDER BY cars.id
    """)
    cars = cur.fetchall()

    cur.execute("""
        SELECT rentals.*, cars.brand, cars.model, customers.name
        FROM rentals
        JOIN cars ON rentals.car_id=cars.id
        JOIN customers ON rentals.customer_id=customers.id
        ORDER BY rentals.id DESC
    """)
    bookings = cur.fetchall()

    cur.execute("""
        SELECT customers.*,
               COUNT(rentals.id) AS booking_count,
               COALESCE(SUM(rentals.total),0) AS total_spent
        FROM customers
        LEFT JOIN rentals ON customers.id=rentals.customer_id
        GROUP BY customers.id
        ORDER BY customers.id DESC
    """)
    customers = cur.fetchall()

    cur.execute("SELECT COUNT(*) AS n FROM cars")
    total_cars = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM customers")
    total_customers = cur.fetchone()["n"]
    cur.execute("SELECT COUNT(*) AS n FROM rentals")
    total_bookings = cur.fetchone()["n"]
    cur.execute("SELECT COALESCE(SUM(total),0) AS rev FROM rentals WHERE status IN ('confirmed','paid','completed')")
    revenue = cur.fetchone()["rev"]

    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()

    cur.close(); conn.close()
    return render_template("admin.html",
        cars=cars, bookings=bookings, customers=customers,
        categories=categories,
        total_cars=total_cars, total_customers=total_customers,
        total_bookings=total_bookings, revenue=revenue
    )


# ── ADD CAR ────────────────────────────────────────────────────
@app.route("/add_car", methods=["POST"])
def add_car():
    if not is_admin(): return redirect("/login")
    brand        = request.form["brand"].strip()
    model        = request.form["model"].strip()
    price        = request.form["price"]
    image        = request.form.get("image", "default-car.jpg").strip() or "default-car.jpg"
    category_id  = request.form.get("category_id") or None
    year         = request.form.get("year") or None
    seats        = request.form.get("seats") or 5
    transmission = request.form.get("transmission", "Automatic")
    fuel_type    = request.form.get("fuel_type", "Petrol")
    color        = request.form.get("color", "").strip() or None
    mileage      = request.form.get("mileage", "Unlimited").strip() or "Unlimited"
    description  = request.form.get("description", "").strip() or None
    features     = request.form.get("features", "").strip() or None
    gallery      = request.form.get("gallery", "").strip() or None

    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO cars (brand, model, year, price_per_day, image, gallery, available,
                          category_id, seats, transmission, fuel_type, color, mileage, description, features)
        VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (brand, model, year, price, image, gallery, category_id,
          seats, transmission, fuel_type, color, mileage, description, features))
    conn.commit(); cur.close(); conn.close()
    flash(f"{brand} {model} added to fleet.")
    return redirect("/admin")


# ── EDIT CAR ────────────────────────────────────────────────────
@app.route("/edit_car/<int:id>", methods=["POST"])
def edit_car(id):
    if not is_admin(): return redirect("/login")
    brand        = request.form["brand"].strip()
    model        = request.form["model"].strip()
    price        = request.form["price"]
    image        = request.form.get("image", "").strip() or "default-car.jpg"
    category_id  = request.form.get("category_id") or None
    year         = request.form.get("year") or None
    seats        = request.form.get("seats") or 5
    transmission = request.form.get("transmission", "Automatic")
    fuel_type    = request.form.get("fuel_type", "Petrol")
    color        = request.form.get("color", "").strip() or None
    mileage      = request.form.get("mileage", "Unlimited").strip() or "Unlimited"
    description  = request.form.get("description", "").strip() or None
    features     = request.form.get("features", "").strip() or None
    gallery      = request.form.get("gallery", "").strip() or None
    available    = int(request.form.get("available", 1))

    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        UPDATE cars SET
            brand=%s, model=%s, year=%s, price_per_day=%s, image=%s, gallery=%s,
            available=%s, category_id=%s, seats=%s, transmission=%s, fuel_type=%s,
            color=%s, mileage=%s, description=%s, features=%s
        WHERE id=%s
    """, (brand, model, year, price, image, gallery, available, category_id,
          seats, transmission, fuel_type, color, mileage, description, features, id))
    conn.commit(); cur.close(); conn.close()
    flash(f"{brand} {model} updated successfully.")
    return redirect("/admin")


# ── DELETE CAR ─────────────────────────────────────────────────
@app.route("/delete_car/<int:id>")
def delete_car(id):
    if not is_admin(): return redirect("/login")
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM cars WHERE id=%s", (id,))
    conn.commit(); cur.close(); conn.close()
    flash("Vehicle removed from fleet.")
    return redirect("/admin")


# ── TOGGLE CAR AVAILABILITY ────────────────────────────────────
@app.route("/toggle_car/<int:id>/<int:status>")
def toggle_car(id, status):
    if not is_admin(): return redirect("/login")
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE cars SET available=%s WHERE id=%s", (status, id))
    conn.commit(); cur.close(); conn.close()
    flash("Vehicle availability updated.")
    return redirect("/admin")


# ── UPDATE BOOKING STATUS ──────────────────────────────────────
@app.route("/update_status/<int:id>/<status>")
def update_status(id, status):
    if not is_admin(): return redirect("/login")
    allowed = ['pending', 'confirmed', 'completed', 'cancelled']
    if status not in allowed: return redirect("/admin")
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE rentals SET status=%s WHERE id=%s", (status, id))
    conn.commit(); cur.close(); conn.close()
    flash("Booking status updated.")
    return redirect("/admin")


# ── 404 ────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)