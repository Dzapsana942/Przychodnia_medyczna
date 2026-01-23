from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_conn, init_db
from database import get_doctor_schedule, add_schedule
import datetime
from datetime import date as dt_date, datetime as dt_datetime, timedelta
import re

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "super_secret_key"

# ---------------------------
# INIT DATABASE
# ---------------------------
init_db()

# ---------------------------
# DANE „ROKSA” – MOCK DLA SYSTEMU REZERWACJI
# ---------------------------

doctors = [
    {"id": 1, "name": "dr Anna Kowalska"},
    {"id": 2, "name": "dr Piotr Nowak"},
    {"id": 3, "name": "dr Maria Zielińska"},
]

appointments: list[dict] = []
next_appointment_id = 1
AVG_VISIT_MIN = 15


def get_slots_for(selected_date: str):
    """Mock slotów – na razie bez DB, ale działa do prezentacji."""
    return [
        {
            "slot_id": 101,
            "doctor_id": 1,
            "doctor_name": "dr Anna Kowalska",
            "date": selected_date,
            "time": "09:00",
        },
        {
            "slot_id": 102,
            "doctor_id": 1,
            "doctor_name": "dr Anna Kowalska",
            "date": selected_date,
            "time": "09:30",
        },
        {
            "slot_id": 201,
            "doctor_id": 2,
            "doctor_name": "dr Piotr Nowak",
            "date": selected_date,
            "time": "10:00",
        },
        {
            "slot_id": 202,
            "doctor_id": 2,
            "doctor_name": "dr Piotr Nowak",
            "date": selected_date,
            "time": "10:30",
        },
        {
            "slot_id": 301,
            "doctor_id": 3,
            "doctor_name": "dr Maria Zielińska",
            "date": selected_date,
            "time": "11:00",
        },
    ]


# ---------------------------
# HELPERS
# ---------------------------

from functools import wraps

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Musisz się zalogować!", "danger")
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapper



def get_eta(position, avg_minutes=15):
    now = datetime.datetime.now()
    eta = now + datetime.timedelta(minutes=position * avg_minutes)
    return eta.strftime("%H:%M")


# ---------------------------
# ROUTES – LOGOWANIE / PANELE Z BAZY (ANIA)
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

    doctors_db = conn.execute(
        "SELECT * FROM doctors"
    ).fetchall()

    conn.close()

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
        doctors=doctors_db,
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

    from datetime import datetime as dt_now, timedelta as td
    AVG_VISIT_MIN_LOCAL = 15

    patients_with_visit_time = []
    for idx, p in enumerate(patients):
        visit_time = (
            dt_now.now() + td(minutes=idx * AVG_VISIT_MIN_LOCAL)
        ).strftime("%H:%M")

        patient_dict = dict(p)
        patient_dict["visit_time"] = visit_time
        patients_with_visit_time.append(patient_dict)

    return render_template(
        "doctor.html",
        patients=patients_with_visit_time,
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
def doctors_view():
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

    doctors_db = conn.execute(
        "SELECT * FROM doctors"
    ).fetchall()
    conn.close()

    return render_template("doctors.html", doctors=doctors_db)


@app.route("/doctors/edit/<int:doctor_id>", methods=["GET", "POST"])
@login_required
def edit_doctor(doctor_id):
    conn = get_conn()

    if request.method == "POST":
        # Odbieramy dane z formularza
        name = request.form["name"]
        hours = request.form["hours"]

        # Aktualizujemy zarówno imię/nazwisko, jak i godziny
        conn.execute(
            "UPDATE doctors SET name=?, hours=? WHERE id=?",
            (name, hours, doctor_id)
        )
        conn.commit()
        conn.close()
        flash("Dane lekarza zaktualizowane!", "success")
        return redirect(url_for("doctors_view"))

    # Pobieramy dane lekarza
    doctor = conn.execute(
        "SELECT * FROM doctors WHERE id=?",
        (doctor_id,)
    ).fetchone()
    conn.close()

    return render_template("edit_doctor.html", doctor=doctor)
@login_required
def delete_doctor(doctor_id):
    conn = get_conn()
    conn.execute("DELETE FROM doctors WHERE id=?", (doctor_id,))
    conn.commit()
    conn.close()
    flash("Lekarz został usunięty!", "success")
    return redirect(url_for("doctors_view"))

app.add_url_rule('/doctors/delete/<int:doctor_id>', view_func=delete_doctor, methods=['POST'])
@app.route("/appointments")
@login_required
def appointments_view():
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

        last_pos = conn.execute(
            "SELECT MAX(position) AS maxpos FROM patients"
        ).fetchone()["maxpos"]
        next_pos = 1 if last_pos is None else last_pos + 1
        conn.execute(
            "INSERT INTO patients (name, doctor_id, position, status) VALUES (?, ?, ?, 'oczekuje')",
            (name, appointment_id, next_pos)
        )
        conn.execute(
            "UPDATE appointments SET status='zarezerwowany', patient_id=(SELECT MAX(id) FROM patients) WHERE id=?",
            (appointment_id,)
        )
        conn.commit()
        conn.close()

        flash(f"Rezerwacja zapisana! Twój numer w kolejce: {next_pos}", "success")
        return redirect(url_for("appointments_view"))

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

    flash("Grafik zapisany", "success")
    return redirect(f"/doctor/{doctor_id}/schedule")


# ---------------------------
# ROUTES – CZĘŚĆ ROKSY (PACJENT + PANEL REJESTRATORKI)
# ---------------------------

# Strona startowa systemu rezerwacji (żeby nie nadpisywać /login)
@app.route("/public")
def public_home():
    return render_template("base.html")


@app.route("/slots")
def show_slots():
    doctor_id = request.args.get("doctor_id", default=1, type=int)
    selected_date = request.args.get("date") or dt_date.today().isoformat()

    all_slots = get_slots_for(selected_date)

    booked_slot_ids = {
        a["slot_id"]
        for a in appointments
        if a["date"] == selected_date and a["status"] == "BOOKED"
    }

    slots = [
        s for s in all_slots
        if s["doctor_id"] == doctor_id and s["slot_id"] not in booked_slot_ids
    ]

    return render_template(
        "slots.html",
        doctors=doctors,
        slots=slots,
        selected_doctor_id=doctor_id,
        selected_date=selected_date,
    )


@app.route("/book")
def book_form():
    slot_id = request.args.get("slot_id", type=int)
    date = request.args.get("date")

    if slot_id is None or date is None:
        return "Brak wymaganych parametrów.", 400

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)

    if slot is None:
        return "Nie znaleziono wybranego terminu.", 404

    already_booked = any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    )
    if already_booked:
        return (
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            400,
        )

    return render_template("book.html", slot=slot)


@app.route("/confirm", methods=["POST"])
def confirm():
    global next_appointment_id

    slot_id = request.form.get("slot_id", type=int)
    patient_name = request.form.get("patient_name", "").strip()
    email = request.form.get("email", "").strip()
    reason = request.form.get("reason", "")
    date = request.form.get("date")

    if len(patient_name) < 3:
        return (
            "<h3>Błąd ❌</h3>"
            "<p>Imię i nazwisko musi mieć co najmniej 3 znaki.</p>"
            "<a href='/slots'>Wróć</a>",
            400,
        )

    email_regex = r"^[^@]+@[^@]+\.[^@]+$"
    if not re.match(email_regex, email):
        return (
            "<h3>Błąd ❌</h3>"
            "<p>Niepoprawny adres e-mail.</p>"
            "<a href='/slots'>Wróć</a>",
            400,
        )

    if slot_id is None or date is None:
        return "Brak danych rezerwacji.", 400

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return "Nie znaleziono terminu do rezerwacji.", 404

    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    ):
        return (
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            400,
        )

    appt = {
        "id": next_appointment_id,
        "slot_id": slot_id,
        "doctor_id": slot["doctor_id"],
        "doctor_name": slot["doctor_name"],
        "date": slot["date"],
        "time": slot["time"],
        "patient_name": patient_name,
        "email": email,
        "reason": reason,
        "status": "BOOKED",
    }
    appointments.append(appt)
    next_appointment_id += 1

    todays = [
        a for a in appointments
        if a["doctor_id"] == appt["doctor_id"]
        and a["date"] == appt["date"]
        and a["status"] == "BOOKED"
    ]
    todays_sorted = sorted(todays, key=lambda x: x["time"])
    queue_number = [a["id"] for a in todays_sorted].index(appt["id"]) + 1

    start = dt_datetime.strptime(appt["date"] + " " + appt["time"], "%Y-%m-%d %H:%M")
    estimated_dt = start + timedelta(minutes=(queue_number - 1) * AVG_VISIT_MIN)
    estimated_time = estimated_dt.strftime("%H:%M")

    return render_template(
        "confirm.html",
        patient_name=patient_name,
        queue_number=queue_number,
        estimated_time=estimated_time,
        appointment_id=appt["id"],
    )


@app.route("/cancel/<int:appointment_id>")
def cancel_appointment(appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None:
        return "Nie znaleziono rezerwacji.", 404

    appt["status"] = "CANCELLED"

    return render_template("cancel.html", appointment=appt)


@app.route("/reschedule/<int:appointment_id>")
def reschedule_form(appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None or appt["status"] != "BOOKED":
        return "Nie znaleziono aktywnej rezerwacji.", 404

    selected_date = request.args.get("date") or appt["date"]
    all_slots = get_slots_for(selected_date)

    booked_slot_ids = {
        a["slot_id"]
        for a in appointments
        if a["doctor_id"] == appt["doctor_id"]
        and a["date"] == selected_date
        and a["status"] == "BOOKED"
        and a["id"] != appointment_id
    }

    slots = [
        s for s in all_slots
        if s["doctor_id"] == appt["doctor_id"]
        and s["slot_id"] not in booked_slot_ids
    ]

    return render_template(
        "reschedule.html",
        appointment=appt,
        slots=slots,
        selected_date=selected_date,
    )


@app.route("/reschedule/<int:appointment_id>", methods=["POST"])
def reschedule_save(appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None or appt["status"] != "BOOKED":
        return "Nie znaleziono aktywnej rezerwacji.", 404

    slot_id = request.form.get("slot_id", type=int)
    date = request.form.get("date")

    if slot_id is None or date is None:
        return "Brak danych.", 400

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return "Nie znaleziono wybranego terminu.", 404

    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        and a["id"] != appointment_id
        for a in appointments
    ):
        return (
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            400,
        )

    appt["slot_id"] = slot_id
    appt["doctor_id"] = slot["doctor_id"]
    appt["doctor_name"] = slot["doctor_name"]
    appt["date"] = slot["date"]
    appt["time"] = slot["time"]

    todays = [
        a for a in appointments
        if a["doctor_id"] == appt["doctor_id"]
        and a["date"] == appt["date"]
        and a["status"] == "BOOKED"
    ]
    todays_sorted = sorted(todays, key=lambda x: x["time"])
    queue_number = [a["id"] for a in todays_sorted].index(appt["id"]) + 1

    start = dt_datetime.strptime(appt["date"] + " " + appt["time"], "%Y-%m-%d %H:%M")
    estimated_dt = start + timedelta(minutes=(queue_number - 1) * AVG_VISIT_MIN)
    estimated_time = estimated_dt.strftime("%H:%M")

    return render_template(
        "confirm.html",
        patient_name=appt["patient_name"],
        queue_number=queue_number,
        estimated_time=estimated_time,
        appointment_id=appt["id"],
    )


@app.route("/desk")
def desk():
    doctor_id = request.args.get("doctor_id", type=int)
    selected_doctor_id = doctor_id or doctors[0]["id"]
    selected_date = request.args.get("date") or dt_date.today().isoformat()

    all_slots = get_slots_for(selected_date)

    booked_slot_ids = {
        a["slot_id"]
        for a in appointments
        if a["doctor_id"] == selected_doctor_id
        and a["date"] == selected_date
        and a["status"] == "BOOKED"
    }

    free_slots = [
        s for s in all_slots
        if s["doctor_id"] == selected_doctor_id
        and s["slot_id"] not in booked_slot_ids
    ]

    return render_template(
        "desk.html",
        doctors=doctors,
        selected_doctor_id=selected_doctor_id,
        selected_date=selected_date,
        free_slots=free_slots,
        created_appt=None,
    )


@app.route("/desk", methods=["POST"])
def desk_add():
    global next_appointment_id

    patient_name = request.form.get("patient_name", "").strip()
    slot_id = request.form.get("slot_id", type=int)
    date = request.form.get("date")

    if not patient_name or slot_id is None or date is None:
        return "Brak wymaganych danych.", 400

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return "Nie znaleziono wybranego terminu.", 404

    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    ):
        return (
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/desk'>Wróć do panelu rejestratorki</a>",
            400,
        )

    appt = {
        "id": next_appointment_id,
        "slot_id": slot_id,
        "doctor_id": slot["doctor_id"],
        "doctor_name": slot["doctor_name"],
        "date": slot["date"],
        "time": slot["time"],
        "patient_name": patient_name,
        "email": None,
        "reason": None,
        "status": "BOOKED",
    }
    appointments.append(appt)
    next_appointment_id += 1

    selected_doctor_id = slot["doctor_id"]
    selected_date = date

    all_slots = get_slots_for(selected_date)
    booked_slot_ids = {
        a["slot_id"]
        for a in appointments
        if a["doctor_id"] == selected_doctor_id
        and a["date"] == selected_date
        and a["status"] == "BOOKED"
    }
    free_slots = [
        s for s in all_slots
        if s["doctor_id"] == selected_doctor_id
        and s["slot_id"] not in booked_slot_ids
    ]

    return render_template(
        "desk.html",
        doctors=doctors,
        selected_doctor_id=selected_doctor_id,
        selected_date=selected_date,
        free_slots=free_slots,
        created_appt=appt,
    )


if __name__ == "__main__":
    app.run(debug=True)

