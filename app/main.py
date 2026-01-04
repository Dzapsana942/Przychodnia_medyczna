from datetime import date as dt_date, datetime, timedelta

from fastapi import FastAPI, Form, Request
import re
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates



app = FastAPI(title="Przychodnia Medyczna")
templates = Jinja2Templates(directory="app/templates")

# ===== "Baza" w pamięci (na start) =====
appointments = []          # lista rezerwacji
next_appointment_id = 1    # auto-ID
AVG_VISIT_MIN = 15         # średni czas wizyty (min)


# ===== Strona główna =====
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request})


# ===== Dostępne terminy =====
@app.get("/slots", response_class=HTMLResponse)
def show_slots(request: Request, doctor_id: int = 1, date: str | None = None):
    doctors = [
        {"id": 1, "name": "dr Anna Kowalska"},
        {"id": 2, "name": "dr Piotr Nowak"},
        {"id": 3, "name": "dr Maria Zielińska"},
    ]

    selected_date = date or dt_date.today().isoformat()
    all_slots = get_slots_for(selected_date)
    slots = [s for s in all_slots if s["doctor_id"] == doctor_id]

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


# ===== Formularz rezerwacji =====
@app.get("/book", response_class=HTMLResponse)
def book_form(request: Request, slot_id: int, date: str):
    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)

    if slot is None:
        return HTMLResponse("Nie znaleziono wybranego terminu.", status_code=404)

    return templates.TemplateResponse("book.html", {"request": request, "slot": slot})


# ===== Potwierdzenie rezerwacji (zapis + kolejka) =====
@app.post("/confirm", response_class=HTMLResponse)
def confirm(
    request: Request,
    slot_id: int = Form(...),
    patient_name: str = Form(...),
    email: str = Form(...),
    reason: str = Form(""),
    date: str = Form(...),  # <-- dodamy to do book.html jako hidden input
):
    global next_appointment_id
    # ===== WALIDACJE BACKEND =====

    if len(patient_name.strip()) < 3:
        return HTMLResponse(
            "<h3>Błąd ❌</h3>"
            "<p>Imię i nazwisko musi mieć co najmniej 3 znaki.</p>"
            "<a href='/slots'>Wróć</a>",
            status_code=400
        )

    email_regex = r"^[^@]+@[^@]+\.[^@]+$"
    if not re.match(email_regex, email):
        return HTMLResponse(
            "<h3>Błąd ❌</h3>"
            "<p>Niepoprawny adres e-mail.</p>"
            "<a href='/slots'>Wróć</a>",
            status_code=400
        )


    # slot z konkretnej daty
    all_slots = get_slots_for(date)
    slot = next((s for s in all_slots if s["slot_id"] == slot_id), None)
    if slot is None:
        return HTMLResponse("Nie znaleziono terminu do rezerwacji.", status_code=404)

    # zapis rezerwacji
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
        "status": "BOOKED",  # BOOKED / CANCELLED
    }
    appointments.append(appt)
    next_appointment_id += 1

    # kolejka tylko dla tego lekarza + tej daty + aktywne
    todays = [
        a for a in appointments
        if a["doctor_id"] == appt["doctor_id"]
        and a["date"] == appt["date"]
        and a["status"] == "BOOKED"
    ]
    todays_sorted = sorted(todays, key=lambda x: x["time"])
    queue_number = [a["id"] for a in todays_sorted].index(appt["id"]) + 1

    # przybliżony czas wejścia
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


# ===== Anulowanie =====
@app.get("/cancel/{appointment_id}", response_class=HTMLResponse)
def cancel_appointment(request: Request, appointment_id: int):
    appt = next((a for a in appointments if a["id"] == appointment_id), None)
    if appt is None:
        return HTMLResponse("Nie znaleziono rezerwacji.", status_code=404)

    appt["status"] = "CANCELLED"

    return HTMLResponse(
        f"<h2>Anulowano rezerwację ✅</h2>"
        f"<p>ID: {appointment_id}</p>"
        f"<a href='/slots'>Wróć do terminów</a>"
    )


# ===== Slots (mock) =====
def get_slots_for(selected_date: str):
    return [
        {"slot_id": 101, "doctor_id": 1, "doctor_name": "dr Anna Kowalska",  "date": selected_date, "time": "09:00"},
        {"slot_id": 102, "doctor_id": 1, "doctor_name": "dr Anna Kowalska",  "date": selected_date, "time": "09:30"},
        {"slot_id": 201, "doctor_id": 2, "doctor_name": "dr Piotr Nowak",    "date": selected_date, "time": "10:00"},
        {"slot_id": 202, "doctor_id": 2, "doctor_name": "dr Piotr Nowak",    "date": selected_date, "time": "10:30"},
        {"slot_id": 301, "doctor_id": 3, "doctor_name": "dr Maria Zielińska","date": selected_date, "time": "11:00"},
    ]
