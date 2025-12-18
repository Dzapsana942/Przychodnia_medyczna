TESTS.md (TESTY MUST – funkcje pacjenta)
Środowisko testowe

Aplikacja: FastAPI + Jinja2 + Bootstrap

Uruchomienie: uvicorn app.main:app --reload

Adres: http://127.0.0.1:8000

MUST-01 – Wyświetlenie dostępnych terminów

Cel: Pacjent widzi dostępne terminy.
Kroki:

Wejdź na http://127.0.0.1:8000/slots

Sprawdź, czy widoczna jest lista terminów i przycisk „Rezerwuj”.
Oczekiwany rezultat: Strona ładuje się poprawnie, terminy są widoczne.

MUST-02 – Zmiana lekarza na liście terminów

Cel: Pacjent może wybrać innego lekarza.
Kroki:

Wejdź na /slots

Zmień lekarza (select / wybór lekarza).
Oczekiwany rezultat: Lista terminów aktualizuje się pod wybranego lekarza.

MUST-03 – Otwarcie formularza rezerwacji z poprawnymi danymi

Cel: Formularz pokazuje poprawny termin.
Kroki:

Wejdź na /slots

Kliknij „Rezerwuj” przy terminie (np. 09:30)
Oczekiwany rezultat: Otwiera się /book?... i formularz pokazuje właściwego lekarza, datę i godzinę.

MUST-04 – Walidacja frontendu: brak wymaganych pól

Cel: Formularz nie pozwala wysłać pustych danych.
Kroki:

Wejdź na formularz rezerwacji /book?...

Nie wpisuj imienia i e-maila

Kliknij „Potwierdź rezerwację”
Oczekiwany rezultat: Przeglądarka blokuje wysłanie formularza (required).

MUST-05 – Walidacja frontendu: niepoprawny e-mail

Cel: Przeglądarka wykrywa zły email.
Kroki:

Wejdź na /book?...

Wpisz email: abc

Kliknij „Potwierdź rezerwację”
Oczekiwany rezultat: Przeglądarka zgłasza błąd pola email.

MUST-06 – Walidacja backendu: zbyt krótkie imię/nazwisko

Cel: Backend blokuje niepoprawne dane.
Kroki:

Wejdź na /book?...

Wpisz imię i nazwisko: aa

Wpisz poprawny email

Kliknij „Potwierdź rezerwację”
Oczekiwany rezultat: Backend zwraca komunikat błędu (np. „Imię i nazwisko musi mieć co najmniej 3 znaki.”)

MUST-07 – Potwierdzenie rezerwacji + numer w kolejce

Cel: Po rezerwacji pacjent widzi potwierdzenie.
Kroki:

Wejdź na /book?...

Wpisz poprawne dane

Kliknij „Potwierdź rezerwację”
Oczekiwany rezultat: Strona potwierdzenia pokazuje:

imię pacjenta

numer w kolejce

przybliżony czas wejścia

MUST-08 – Kolejka rośnie po kolejnych rezerwacjach

Cel: Kolejka zwiększa się wraz z rezerwacjami.
Kroki:

Zrób rezerwację na ten sam dzień i lekarza (np. 09:00)

Zrób drugą rezerwację na ten sam dzień i lekarza (np. 09:30)
Oczekiwany rezultat: Druga rezerwacja ma numer w kolejce większy (np. 2).