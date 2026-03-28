import os
from flask import Flask, render_template, request, redirect, flash, jsonify, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import csv
import io

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed — rely on real environment variables

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-do-not-use-in-production")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access your bills."

DBN = "db.sqlite"

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(DBN)

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bills (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                name     TEXT    NOT NULL,
                currency TEXT    NOT NULL DEFAULT 'KSH',
                created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                name    TEXT    NOT NULL,
                amount  REAL    NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id)
            );
        """)

init_db()

# ── Auth helpers ───────────────────────────────────────────────────────────────

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id=?", (user_id,)).fetchone()
    if row:
        return User(row[0], row[1])
    return None

# ── Bill splitting logic ───────────────────────────────────────────────────────

def calculate(payments):
    if not payments:
        return 0, 0, []
    total = sum(p["amount"] for p in payments)
    share = round(total / len(payments), 2)
    balances  = {p["name"]: round(p["amount"] - share, 2) for p in payments}
    creditors = {k: v  for k, v in balances.items() if v > 0}
    debtors   = {k: -v for k, v in balances.items() if v < 0}
    transactions = []
    while creditors and debtors:
        c, ca = max(creditors.items(), key=lambda x: x[1])
        d, da = max(debtors.items(),   key=lambda x: x[1])
        pay = round(min(ca, da), 2)
        transactions.append({"from": d, "to": c, "amount": pay})
        creditors[c] = round(creditors[c] - pay, 2)
        debtors[d]   = round(debtors[d]   - pay, 2)
        if creditors[c] == 0: del creditors[c]
        if debtors[d]   == 0: del debtors[d]
    return total, share, transactions

# ── Auth routes ────────────────────────────────────────────────────────────────

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password are required.")
            return redirect("/register")
        hashed = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed))
            flash("Account created! Please log in.")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Username already taken.")
            return redirect("/register")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        with get_db() as conn:
            row = conn.execute("SELECT id, username, password FROM users WHERE username=?", (username,)).fetchone()
        if row and check_password_hash(row[2], password):
            login_user(User(row[0], row[1]))
            return redirect("/")
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")

# ── Bill routes ────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    with get_db() as conn:
        bills = conn.execute(
            "SELECT id, name, currency, created FROM bills WHERE user_id=? ORDER BY created DESC",
            (current_user.id,)
        ).fetchall()
    return render_template("index.html", bills=bills)

@app.route("/bill/new", methods=["GET", "POST"])
@login_required
def new_bill():
    if request.method == "POST":
        name     = request.form["name"].strip()
        currency = request.form.get("currency", "KSH")
        if not name:
            flash("Bill name is required.")
            return redirect("/bill/new")
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO bills (user_id, name, currency) VALUES (?,?,?)",
                (current_user.id, name, currency)
            )
            bill_id = cur.lastrowid
        return redirect(f"/bill/{bill_id}")
    return render_template("new_bill.html")

@app.route("/bill/<int:bill_id>")
@login_required
def bill(bill_id):
    with get_db() as conn:
        b = conn.execute("SELECT id, name, currency FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
        if not b:
            flash("Bill not found.")
            return redirect("/")
        payments = conn.execute(
            "SELECT id, name, amount FROM payments WHERE bill_id=?", (bill_id,)
        ).fetchall()
    payments_list = [{"id": r[0], "name": r[1], "amount": r[2]} for r in payments]
    total, share, transactions = calculate(payments_list)
    tx_strings = [f"{t['from']} pays {t['to']} {b[2]} {t['amount']:.2f}" for t in transactions]
    return render_template("bill.html",
        bill={"id": b[0], "name": b[1], "currency": b[2]},
        payments=payments_list,
        total=total, share=share,
        transactions=tx_strings
    )

@app.route("/bill/<int:bill_id>/add", methods=["POST"])
@login_required
def add_payment(bill_id):
    with get_db() as conn:
        b = conn.execute("SELECT id FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
    if not b:
        flash("Bill not found.")
        return redirect("/")
    name   = request.form["name"].strip()
    amount = request.form["amount"]
    if not name:
        flash("Name is required.")
        return redirect(f"/bill/{bill_id}")
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash("Amount must be a positive number.")
        return redirect(f"/bill/{bill_id}")
    with get_db() as conn:
        conn.execute("INSERT INTO payments (bill_id, name, amount) VALUES (?,?,?)",
                     (bill_id, name, amount))
    flash(f"Payment for {name} added.")
    return redirect(f"/bill/{bill_id}")

@app.route("/bill/<int:bill_id>/edit/<int:payment_id>", methods=["GET", "POST"])
@login_required
def edit_payment(bill_id, payment_id):
    with get_db() as conn:
        b = conn.execute("SELECT id, currency FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
        if not b:
            flash("Bill not found.")
            return redirect("/")
        payment = conn.execute("SELECT id, name, amount FROM payments WHERE id=? AND bill_id=?",
                               (payment_id, bill_id)).fetchone()
        if not payment:
            flash("Payment not found.")
            return redirect(f"/bill/{bill_id}")
    if request.method == "POST":
        name   = request.form["name"].strip()
        amount = request.form["amount"]
        if not name:
            flash("Name is required.")
            return redirect(f"/bill/{bill_id}/edit/{payment_id}")
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash("Amount must be a positive number.")
            return redirect(f"/bill/{bill_id}/edit/{payment_id}")
        with get_db() as conn:
            conn.execute("UPDATE payments SET name=?, amount=? WHERE id=?",
                         (name, amount, payment_id))
        flash("Payment updated.")
        return redirect(f"/bill/{bill_id}")
    return render_template("edit_payment.html",
        bill={"id": bill_id, "currency": b[1]},
        payment={"id": payment[0], "name": payment[1], "amount": payment[2]}
    )

@app.route("/bill/<int:bill_id>/delete/<int:payment_id>", methods=["POST"])
@login_required
def delete_payment(bill_id, payment_id):
    with get_db() as conn:
        b = conn.execute("SELECT id FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
    if not b:
        flash("Bill not found.")
        return redirect("/")
    with get_db() as conn:
        conn.execute("DELETE FROM payments WHERE id=? AND bill_id=?", (payment_id, bill_id))
    flash("Payment removed.")
    return redirect(f"/bill/{bill_id}")

@app.route("/bill/<int:bill_id>/delete", methods=["POST"])
@login_required
def delete_bill(bill_id):
    with get_db() as conn:
        b = conn.execute("SELECT id FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
    if not b:
        flash("Bill not found.")
        return redirect("/")
    with get_db() as conn:
        conn.execute("DELETE FROM payments WHERE bill_id=?", (bill_id,))
        conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))
    flash("Bill deleted.")
    return redirect("/")

# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/bill/<int:bill_id>/export")
@login_required
def export_csv(bill_id):
    with get_db() as conn:
        b = conn.execute("SELECT id, name, currency FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
        if not b:
            flash("Bill not found.")
            return redirect("/")
        rows = conn.execute("SELECT name, amount FROM payments WHERE bill_id=?", (bill_id,)).fetchall()
    payments = [{"name": r[0], "amount": r[1]} for r in rows]
    total, share, transactions = calculate(payments)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", f"Amount ({b[2]})"])
    for p in payments:
        writer.writerow([p["name"], f"{p['amount']:.2f}"])
    writer.writerow([])
    writer.writerow(["Total", f"{total:.2f}"])
    writer.writerow(["Each pays", f"{share:.2f}"])
    writer.writerow([])
    writer.writerow(["Settlements"])
    for t in transactions:
        writer.writerow([f"{t['from']} pays {t['to']}", f"{t['amount']:.2f}"])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={b[1].replace(' ','_')}.csv"}
    )

# ── JSON API ───────────────────────────────────────────────────────────────────

@app.route("/api/bill/<int:bill_id>")
@login_required
def api_bill(bill_id):
    with get_db() as conn:
        b = conn.execute("SELECT id, name, currency FROM bills WHERE id=? AND user_id=?",
                         (bill_id, current_user.id)).fetchone()
        if not b:
            return jsonify({"error": "Not found"}), 404
        rows = conn.execute("SELECT id, name, amount FROM payments WHERE bill_id=?", (bill_id,)).fetchall()
    payments = [{"id": r[0], "name": r[1], "amount": r[2]} for r in rows]
    total, share, transactions = calculate(payments)
    return jsonify({
        "bill":         {"id": b[0], "name": b[1], "currency": b[2]},
        "payments":     payments,
        "total":        total,
        "share":        share,
        "transactions": transactions
    })

if __name__ == "__main__":
    app.run(debug=True)