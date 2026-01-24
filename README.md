#  Przychodnia Medyczna – aplikacja webowa (Flask)

Aplikacja webowa typu **MVP** stworzona w Pythonie z użyciem frameworka **Flask**, umożliwiająca:
- rezerwację wizyt lekarskich przez pacjentów,
- obsługę kolejki pacjentów przez rejestratorkę,
- panel lekarza do zarządzania wizytami,
- zarządzanie lekarzami i grafikami.

Projekt został wykonany w ramach zajęć akademickich.

---

##  Autorzy projektu

- **Roksana** – część pacjenta + system rezerwacji wizyt (publiczna)
- **Ania** – panel rejestratorki, panel lekarza, logowanie i baza danych  
- *(trzeci członek zespołu nie brał udziału w finalnej wersji projektu)*

---

##  Funkcjonalności aplikacji

###  Część publiczna (pacjent)
- przegląd dostępnych terminów wizyt,
- wybór lekarza i daty,
- rezerwacja wizyty (formularz),
- potwierdzenie wizyty,
- anulowanie i zmiana terminu wizyty,
- estetyczny interfejs oparty o Bootstrap.

###  Panel rejestratorki
- logowanie do systemu,
- przegląd kolejki pacjentów,
- dodawanie pacjentów do kolejki,
- zmiana kolejności pacjentów,
- oznaczanie pacjentów jako obsłużonych,
- podgląd przybliżonego czasu wizyty (ETA).

###  Panel lekarza
- logowanie do systemu,
- lista pacjentów oczekujących,
- podgląd czasu wizyty,
- dodawanie notatek do pacjentów,
- obsługa kolejki wizyt.

###  Administracja
- zarządzanie lekarzami,
- edycja grafików lekarzy,
- obsługa bazy danych SQLite.

---

##  Technologie

- **Python 3.12**
- **Flask**
- **SQLite**
- **HTML / Jinja2**
- **CSS**
- **Bootstrap 5**
- **Git & GitHub**

---

##  Struktura projektu

Przychodnia_medyczna/
│
├── app.py # główna aplikacja Flask
├── database.py # obsługa bazy danych
├── schema.sql # struktura bazy danych
├── clinic.db # baza SQLite
├── requirements.txt # zależności
│
├── static/
│ └── css/
│ └── style.css # style aplikacji
│
├── templates/
│ ├── base.html
│ ├── login.html
│ ├── dashboard.html
│ ├── doctor.html
│ ├── doctors.html
│ ├── edit_doctor.html
│ ├── appointments.html
│ ├── slots.html
│ ├── book.html
│ ├── confirm.html
│ ├── cancel.html
│ ├── reschedule.html
│ ├── desk.html
│ └── note.html
│
└── README.md

---

##  Uruchomienie projektu lokalnie

### Klonowanie repozytorium
```bash
git clone https://github.com/Dzapsana942/Przychodnia_medyczna.git
cd Przychodnia_medyczna
Instalacja zależności
pip install -r requirements.txt
Uruchomienie aplikacji
python app.py
Otwórz w przeglądarce
http://127.0.0.1:5000
Dane logowania (testowe)
Rejestratorka
login: rejestratorka
hasło: haslo123
Lekarz
login: lekarz
hasło: haslo123
