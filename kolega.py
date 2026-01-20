from datetime import date as dt_date, datetime, timedelta
import re

from flask import Flask, render_template, request

# ================== APLIKACJA ==================

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

# ================== DANE NA SZTYWNO ==================

doctors = [
    {"id": 1, "name": "dr Anna Kowalska"},
    {"id": 2, "name": "dr Piotr Nowak"},
    {"id": 3, "name": "dr Maria Zielińska"},
]

appointments: list[dict] = []
next_appointment_id = 1
AVG_VISIT_MIN = 15


# ================== STRONA GŁÓWNA ==================

@app.route("/")
def home():
    return render_template("base.html")


# ================== DOSTĘPNE TERMINY (PACJENT) ==================

@app.route("/slots")
def show_slots():
    doctor_id = request.args.get("doctor_id", default=1, type=int)
    selected_date = request.args.get("date") or dt_date.today().isoformat()

    all_slots = get_slots_for(selected_date)

    # zajęte sloty w danym dniu (wszyscy lekarze)
    booked_slot_ids = {
        a["slot_id"]
        for a in appointments
        if a["date"] == selected_date and a["status"] == "BOOKED"
    }

    # wolne sloty wybranego lekarza
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


# ================== FORMULARZ REZERWACJI (PACJENT) ==================

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

    # sprawdzamy, czy termin nie jest już zajęty
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


# ================== POTWIERDZENIE REZERWACJI (ZAPIS + KOLEJKA) ==================

@app.route("/confirm", methods=["POST"])
def confirm():
    global next_appointment_id

    slot_id = request.form.get("slot_id", type=int)
    patient_name = request.form.get("patient_name", "").strip()
    email = request.form.get("email", "").strip()
    reason = request.form.get("reason", "")
    date = request.form.get("date")

    # ---- walidacje ----
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

    # ---- szukamy slotu ----
    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return "Nie znaleziono terminu do rezerwacji.", 404

    # czy slot nie został już zajęty?
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

    # ---- zapis rezerwacji ----
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

    # ---- kolejka ----
    todays = [
        a for a in appointments
        if a["doctor_id"] == appt["doctor_id"]
        and a["date"] == appt["date"]
        and a["status"] == "BOOKED"
    ]
    todays_sorted = sorted(todays, key=lambda x: x["time"])
    queue_number = [a["id"] for a in todays_sorted].index(appt["id"]) + 1

    # ---- przybliżony czas wejścia ----
    start = datetime.strptime(appt["date"] + " " + appt["time"], "%Y-%m-%d %H:%M")
    estimated_dt = start + timedelta(minutes=(queue_number - 1) * AVG_VISIT_MIN)
    estimated_time = estimated_dt.strftime("%H:%M")

    return render_template(
        "confirm.html",
        patient_name=patient_name,
        queue_number=queue_number,
        estimated_time=estimated_time,
        appointment_id=appt["id"],
    )


# ================== ANULOWANIE ==================

@app.route("/cancel/<int:appointment_id>")
def cancel_appointment(appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None:
        return "Nie znaleziono rezerwacji.", 404

    appt["status"] = "CANCELLED"

    return render_template("cancel.html", appointment=appt)


# ================== ZMIANA REZERWACJI ==================

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

    start = datetime.strptime(appt["date"] + " " + appt["time"], "%Y-%m-%d %H:%M")
    estimated_dt = start + timedelta(minutes=(queue_number - 1) * AVG_VISIT_MIN)
    estimated_time = estimated_dt.strftime("%H:%M")

    return render_template(
        "confirm.html",
        patient_name=appt["patient_name"],
        queue_number=queue_number,
        estimated_time=estimated_time,
        appointment_id=appt["id"],
    )


# ================== PANEL REJESTRATORKI ==================

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


# ================== MOCK SLOTTÓW ==================

def get_slots_for(selected_date: str):
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


if __name__ == "__main__":
    app.run(debug=True)
