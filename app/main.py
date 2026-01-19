from datetime import date as dt_date, datetime, timedelta
import re

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# ================== APLIKACJA ==================

app = FastAPI(title="Przychodnia Medyczna")

# statyczne pliki (CSS, obrazki itp.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# szablony HTML
templates = Jinja2Templates(directory="app/templates")

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

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})


# ================== DOSTĘPNE TERMINY (PACJENT) ==================

@app.get("/slots", response_class=HTMLResponse)
def show_slots(
    request: Request,
    doctor_id: int = 1,
    date: str | None = None,
):
    selected_date = date or dt_date.today().isoformat()
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

    return templates.TemplateResponse(
        "slots.html",
        {
            "request": request,
            "doctors": doctors,
            "slots": slots,
            "selected_doctor_id": doctor_id,
            "selected_date": selected_date,
        },
    )


# ================== FORMULARZ REZERWACJI (PACJENT) ==================

@app.get("/book", response_class=HTMLResponse)
def book_form(request: Request, slot_id: int, date: str):
    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)

    if slot is None:
        return HTMLResponse("Nie znaleziono wybranego terminu.", status_code=404)

    # sprawdzamy, czy termin nie jest już zajęty
    already_booked = any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    )
    if already_booked:
        return HTMLResponse(
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            status_code=400,
        )

    return templates.TemplateResponse("book.html", {"request": request, "slot": slot})


# ================== POTWIERDZENIE REZERWACJI (ZAPIS + KOLEJKA) ==================

@app.post("/confirm", response_class=HTMLResponse)
def confirm(
    request: Request,
    slot_id: int = Form(...),
    patient_name: str = Form(...),
    email: str = Form(...),
    reason: str = Form(""),
    date: str = Form(...),
):
    global next_appointment_id

    # ---- walidacje ----
    if len(patient_name.strip()) < 3:
        return HTMLResponse(
            "<h3>Błąd ❌</h3>"
            "<p>Imię i nazwisko musi mieć co najmniej 3 znaki.</p>"
            "<a href='/slots'>Wróć</a>",
            status_code=400,
        )

    email_regex = r"^[^@]+@[^@]+\.[^@]+$"
    if not re.match(email_regex, email):
        return HTMLResponse(
            "<h3>Błąd ❌</h3>"
            "<p>Niepoprawny adres e-mail.</p>"
            "<a href='/slots'>Wróć</a>",
            status_code=400,
        )

    # ---- szukamy slotu ----
    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return HTMLResponse("Nie znaleziono terminu do rezerwacji.", status_code=404)

    # czy slot nie został już zajęty?
    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    ):
        return HTMLResponse(
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            status_code=400,
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

    return templates.TemplateResponse(
        "confirm.html",
        {
            "request": request,
            "patient_name": patient_name,
            "queue_number": queue_number,
            "estimated_time": estimated_time,
            "appointment_id": appt["id"],
        },
    )


# ================== ANULOWANIE ==================

@app.get("/cancel/{appointment_id}", response_class=HTMLResponse)
def cancel_appointment(request: Request, appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None:
        return HTMLResponse("Nie znaleziono rezerwacji.", status_code=404)

    appt["status"] = "CANCELLED"

    return templates.TemplateResponse(
        "cancel.html",
        {
            "request": request,
            "appointment": appt,
        },
    )


# ================== ZMIANA REZERWACJI ==================

@app.get("/reschedule/{appointment_id}", response_class=HTMLResponse)
def reschedule_form(
    request: Request,
    appointment_id: int,
    date: str | None = None,
):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None or appt["status"] != "BOOKED":
        return HTMLResponse("Nie znaleziono aktywnej rezerwacji.", status_code=404)

    selected_date = date or appt["date"]
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

    return templates.TemplateResponse(
        "reschedule.html",
        {
            "request": request,
            "appointment": appt,
            "slots": slots,
            "selected_date": selected_date,
        },
    )


@app.post("/reschedule/{appointment_id}", response_class=HTMLResponse)
def reschedule_save(
    request: Request,
    appointment_id: int,
    slot_id: int = Form(...),
    date: str = Form(...),
):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None or appt["status"] != "BOOKED":
        return HTMLResponse("Nie znaleziono aktywnej rezerwacji.", status_code=404)

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return HTMLResponse("Nie znaleziono wybranego terminu.", status_code=404)

    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        and a["id"] != appointment_id
        for a in appointments
    ):
        return HTMLResponse(
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/slots'>Wróć do dostępnych terminów</a>",
            status_code=400,
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

    return templates.TemplateResponse(
        "confirm.html",
        {
            "request": request,
            "patient_name": appt["patient_name"],
            "queue_number": queue_number,
            "estimated_time": estimated_time,
            "appointment_id": appt["id"],
        },
    )


# ================== PANEL REJESTRATORKI ==================

@app.get("/desk", response_class=HTMLResponse)
def desk(
    request: Request,
    doctor_id: int | None = None,
    date: str | None = None,
):
    selected_doctor_id = doctor_id or doctors[0]["id"]
    selected_date = date or dt_date.today().isoformat()

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

    return templates.TemplateResponse(
        "desk.html",
        {
            "request": request,
            "doctors": doctors,
            "selected_doctor_id": selected_doctor_id,
            "selected_date": selected_date,
            "free_slots": free_slots,
            "created_appt": None,
        },
    )


@app.post("/desk", response_class=HTMLResponse)
def desk_add(
    request: Request,
    patient_name: str = Form(...),
    slot_id: int = Form(...),
    date: str = Form(...),
):
    global next_appointment_id

    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return HTMLResponse("Nie znaleziono wybranego terminu.", status_code=404)

    if any(
        a["slot_id"] == slot_id
        and a["date"] == date
        and a["status"] == "BOOKED"
        for a in appointments
    ):
        return HTMLResponse(
            "<h3>Termin zajęty ❌</h3>"
            "<p>Wybrany termin został już zarezerwowany.</p>"
            "<a href='/desk'>Wróć do panelu rejestratorki</a>",
            status_code=400,
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

    return templates.TemplateResponse(
        "desk.html",
        {
            "request": request,
            "doctors": doctors,
            "selected_doctor_id": selected_doctor_id,
            "selected_date": selected_date,
            "free_slots": free_slots,
            "created_appt": appt,
        },
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
