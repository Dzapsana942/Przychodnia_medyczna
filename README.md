# Przychodnia Medyczna - aplikacja webowa Flask

Aplikacja webowa typu MVP stworzona w Pythonie z użyciem frameworka Flask. Projekt umożliwia rezerwację wizyt lekarskich przez pacjentów, obsługę kolejki pacjentów przez rejestratorkę, panel lekarza do zarządzania wizytami oraz zarządzanie lekarzami i grafikami.

Projekt został wykonany w ramach zajęć akademickich.

## Autorzy projektu

- Roksana - część pacjenta i publiczny system rezerwacji wizyt
- Ania - panel rejestratorki, panel lekarza, logowanie i baza danych

## Funkcjonalności aplikacji

### Część publiczna pacjenta

- przegląd dostępnych terminów wizyt
- wybór lekarza i daty
- rezerwacja wizyty przez formularz
- potwierdzenie wizyty
- anulowanie wizyty
- zmiana terminu wizyty
- interfejs oparty o Bootstrap

### Panel rejestratorki

- logowanie do systemu
- przegląd kolejki pacjentów
- dodawanie pacjentów do kolejki
- zmiana kolejności pacjentów
- oznaczanie pacjentów jako obsłużonych
- podgląd przybliżonego czasu wizyty ETA

### Panel lekarza

- logowanie do systemu
- lista pacjentów oczekujących
- podgląd czasu wizyty
- dodawanie notatek do pacjentów
- obsługa kolejki wizyt

### Administracja

- zarządzanie lekarzami
- edycja grafików lekarzy
- obsługa bazy danych SQLite

## Technologie

- Python 3.12
- Flask
- SQLite
- HTML / Jinja2
- CSS
- Bootstrap 5
- Git / GitHub

## Struktura projektu

```text
Przychodnia_medyczna/
├── app.py
├── database.py
├── schema.sql
├── clinic.db
├── requirements.txt
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── doctor.html
│   ├── doctors.html
│   ├── edit_doctor.html
│   ├── appointments.html
│   ├── slots.html
│   ├── book.html
│   ├── confirm.html
│   ├── cancel.html
│   ├── reschedule.html
│   ├── desk.html
│   └── note.html
└── README.md
```

## Uruchomienie projektu lokalnie

### 1. Klonowanie repozytorium

```bash
git clone https://github.com/Dzapsana942/Przychodnia_medyczna.git
cd Przychodnia_medyczna
```

### 2. Instalacja zależności

```bash
pip install -r requirements.txt
```

### 3. Uruchomienie aplikacji

```bash
python app.py
```

### 4. Otwarcie aplikacji w przeglądarce

```text
http://127.0.0.1:5000
```

## Dane logowania testowe

### Rejestratorka

```text
login: rejestratorka
hasło: haslo123
```

### Lekarz

```text
login: lekarz1
hasło: haslo123
```

## Baza danych

Projekt wykorzystuje bazę SQLite. Struktura bazy znajduje się w pliku `schema.sql`.

Główne tabele:

- `users` - konta użytkowników i role
- `doctors` - lekarze
- `patients` - pacjenci i kolejka
- `appointments` - terminy wizyt
- `doctor_schedule` - grafiki lekarzy

## Najważniejsze elementy projektu

- aplikacja webowa we Flasku
- logowanie i rozróżnienie ról użytkowników
- panel pacjenta, rejestratorki i lekarza
- obsługa rezerwacji wizyt
- kolejka pacjentów
- edycja lekarzy i grafików
- baza danych SQLite
- widoki HTML/Jinja2 i Bootstrap

## Status projektu

Projekt jest wersją MVP przygotowaną w ramach zajęć akademickich. Część funkcjonalności działa na bazie SQLite, a część publicznego systemu rezerwacji wykorzystuje dane demonstracyjne.
