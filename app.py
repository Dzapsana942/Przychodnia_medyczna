from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_conn, init_db
from database import get_doctor_schedule,add_schedule
import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

# ---------------------------
# INIT DATABASE
# ---------------------------
init_db()

# ---------------------------
# HELPERS
# ---------------------------
def login_required(view):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Musisz się zalogować!", "danger")
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper

def get_eta(position, avg_minutes=15):
    now = datetime.datetime.now()
    eta = now + datetime.timedelta(minutes=position * avg_minutes)
    return eta.strftime("%H:%M")

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            if user["role"] == "lekarz":
                return redirect(url_for("doctor_panel"))
            else:
                return redirect(url_for("dashboard"))

        else:
            flash("Złe dane logowania!", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") != "rejestratorka":
        flash("Brak dostępu do panelu rejestratorki", "danger")
        return redirect(url_for("doctor_panel"))

    conn = get_conn()
    patients = conn.execute(
        "SELECT * FROM patients WHERE status='oczekuje' ORDER BY position"
    ).fetchall()

    doctors = conn.execute(
        "SELECT * FROM doctors"
    ).fetchall()

    conn.close()

    # liczenie ETA
    eta_list = []
    for p in patients:
        eta_list.append({
            "id": p["id"],
            "name": p["name"],
            "position": p["position"],
            "eta": get_eta(p["position"] - 1)
        })

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        patients=patients,
        doctors=doctors,
        eta_list=eta_list
    )

@app.route("/doctor")
@login_required
def doctor_panel():
    if session.get("role") != "lekarz":
        flash("Brak dostępu do panelu lekarza", "danger")
        return redirect(url_for("dashboard"))

    conn = get_conn()
    patients = conn.execute("""
        SELECT * FROM patients
        WHERE status='oczekuje'
        ORDER BY position
    """).fetchall()
    conn.close()

    return render_template(
        "doctor.html",
        patients=patients,
        username=session.get("username")
    )


@app.route("/mark_served/<int:patient_id>")
@login_required
def mark_served(patient_id):
    conn = get_conn()
    conn.execute(
        "UPDATE patients SET status='obsłużony' WHERE id=?",
        (patient_id,)
    )
    conn.commit()

    # aktualizacja kolejności
    conn.execute("""
        UPDATE patients
        SET position = position - 1
        WHERE position > (
            SELECT position FROM patients WHERE id=?
        )
    """, (patient_id,))
    conn.commit()
    conn.close()

    flash("Pacjent oznaczony jako obsłużony", "success")
    return redirect(url_for("dashboard"))


@app.route("/move/<int:patient_id>/<direction>")
@login_required
def move(patient_id, direction):
    conn = get_conn()

    current = conn.execute(
        "SELECT id, position FROM patients WHERE id=?",
        (patient_id,)
    ).fetchone()

    if not current:
        flash("Pacjent nie istnieje!", "danger")
        return redirect(url_for("dashboard"))

    pos = current["position"]

    if direction == "up" and pos > 1:
        new_pos = pos - 1
    elif direction == "down":
        new_pos = pos + 1
    else:
        flash("Nie można przesunąć pacjenta", "danger")
        return redirect(url_for("dashboard"))

    # zamiana dwóch pacjentów
    conn.execute("""
        UPDATE patients
        SET position = ?
        WHERE position = ?
    """, (pos, new_pos))

    conn.execute("""
        UPDATE patients
        SET position = ?
        WHERE id = ?
    """, (new_pos, patient_id))

    conn.commit()
    conn.close()

    flash("Pacjent przesunięty", "success")
    return redirect(url_for("dashboard"))
@app.route("/note/<int:patient_id>", methods=["GET", "POST"])
@login_required
def note(patient_id):
    conn = get_conn()

    if request.method == "POST":
        note_text = request.form["note"]
        conn.execute(
            "UPDATE patients SET note=? WHERE id=?",
            (note_text, patient_id)
        )
        conn.commit()
        conn.close()

        flash("Notatka zapisana!", "success")

        if session.get("role") == "lekarz":
            return redirect(url_for("doctor_panel"))
        else:
            return redirect(url_for("dashboard"))

    patient = conn.execute(
        "SELECT * FROM patients WHERE id=?", (patient_id,)
    ).fetchone()
    conn.close()

    if not patient:
        flash("Nie znaleziono pacjenta!", "danger")
        if session.get("role") == "lekarz":
            return redirect(url_for("doctor_panel"))
        else:
            return redirect(url_for("dashboard"))

    return render_template("note.html", patient=patient)


@app.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    name = request.form["name"]
    doctor_id = 1  # na MVP tylko jeden lekarz

    conn = get_conn()

    # ustal kolejny numer w kolejce
    last_pos = conn.execute(
        "SELECT MAX(position) AS maxpos FROM patients"
    ).fetchone()["maxpos"]

    next_pos = 1 if last_pos is None else last_pos + 1

    conn.execute(
        "INSERT INTO patients (name, doctor_id, position, status) VALUES (?, ?, ?, 'oczekuje')",
        (name, doctor_id, next_pos)
    )
    conn.commit()
    conn.close()

    flash("Pacjent dodany do kolejki", "success")
    return redirect(url_for("dashboard"))

@app.route("/doctors", methods=["GET", "POST"])
@login_required
def doctors():
    conn = get_conn()

    if request.method == "POST":
        name = request.form["name"]
        hours = request.form["hours"]

        conn.execute(
            "INSERT INTO doctors (name, hours) VALUES (?, ?)",
            (name, hours)
        )
        conn.commit()
        flash("Lekarz dodany!", "success")

    doctors = conn.execute(
        "SELECT * FROM doctors"
    ).fetchall()
    conn.close()

    return render_template("doctors.html", doctors=doctors)
@app.route("/doctors/edit/<int:doctor_id>", methods=["GET", "POST"])
@login_required
def edit_doctor(doctor_id):
    conn = get_conn()

    if request.method == "POST":
        hours = request.form["hours"]
        conn.execute(
            "UPDATE doctors SET hours=? WHERE id=?",
            (hours, doctor_id)
        )
        conn.commit()
        conn.close()
        flash("Grafik zaktualizowany!", "success")
        return redirect(url_for("doctors"))

    doctor = conn.execute(
        "SELECT * FROM doctors WHERE id=?",
        (doctor_id,)
    ).fetchone()
    conn.close()

    return render_template("edit_doctor.html", doctor=doctor)

@app.route("/appointments")
@login_required
def appointments():
    conn = get_conn()
    available = conn.execute(
        "SELECT a.id, a.appointment_time, d.name AS doctor_name "
        "FROM appointments a "
        "JOIN doctors d ON a.doctor_id = d.id "
        "WHERE a.status='wolny'"
    ).fetchall()
    conn.close()

    return render_template("appointments.html", appointments=available)
@app.route("/reserve/<int:appointment_id>", methods=["GET", "POST"])
@login_required
def reserve_appointment(appointment_id):
    conn = get_conn()

    if request.method == "POST":
        name = request.form["name"]

        # dodanie pacjenta
        last_pos = conn.execute("SELECT MAX(position) AS maxpos FROM patients").fetchone()["maxpos"]
        next_pos = 1 if last_pos is None else last_pos + 1
        conn.execute(
            "INSERT INTO patients (name, doctor_id, position, status) VALUES (?, ?, ?, 'oczekuje')",
            (name, appointment_id, next_pos)
        )
        # aktualizacja statusu terminu
        conn.execute(
            "UPDATE appointments SET status='zarezerwowany', patient_id=(SELECT MAX(id) FROM patients) WHERE id=?",
            (appointment_id,)
        )
        conn.commit()
        conn.close()

        flash(f"Rezerwacja zapisana! Twój numer w kolejce: {next_pos}", "success")
        return redirect(url_for("appointments"))

    appointment = conn.execute(
        "SELECT a.id, a.appointment_time, d.name AS doctor_name "
        "FROM appointments a JOIN doctors d ON a.doctor_id = d.id "
        "WHERE a.id=?", (appointment_id,)
    ).fetchone()
    conn.close()

    return render_template("reserve_form.html", appointment=appointment)
@app.route("/doctor/<int:doctor_id>/schedule")
def doctor_schedule(doctor_id):
    schedule = get_doctor_schedule(doctor_id)
    doctor = {"id": doctor_id}

    return render_template(
        "edit_doctor.html",
        doctor=doctor,
        schedule=schedule
    )
@app.route("/schedule/add", methods=["POST"])
def schedule_add():
    doctor_id = int(request.form["doctor_id"])
    day_of_week = int(request.form["day"])
    start_time = request.form["start_time"]
    end_time = request.form["end_time"]

    add_schedule(doctor_id, day_of_week, start_time, end_time)

    flash("Grafik zapisany ✅", "success")
    return redirect(f"/doctor/{doctor_id}/schedule")


if __name__ == "__main__":
    app.run(debug=True)
