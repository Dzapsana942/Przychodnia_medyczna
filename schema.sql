CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hours TEXT
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'oczekuje',
    doctor_id INTEGER,
    position INTEGER,
    note TEXT,
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
);

INSERT OR IGNORE INTO users (username, password, role) VALUES ('rejestratorka', 'haslo123', 'rejestratorka');

INSERT OR IGNORE INTO doctors (id, name, hours) VALUES (1, 'dr Anna Nowak', '08:00-16:00');

INSERT OR IGNORE INTO patients (name, status, doctor_id, position) VALUES ('Jan Kowalski', 'oczekuje', 1, 1);
INSERT OR IGNORE INTO patients (name, status, doctor_id, position) VALUES ('Maria Zalewska', 'oczekuje', 1, 2);

INSERT INTO users (username, password, role)
VALUES ('lekarz1', 'haslo123', 'lekarz');

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id INTEGER,
    patient_id INTEGER,
    appointment_time TEXT,
    status TEXT DEFAULT 'wolny'
);
INSERT INTO appointments (doctor_id, appointment_time) VALUES (1, '2025-12-18 10:00');
INSERT INTO appointments (doctor_id, appointment_time) VALUES (1, '2025-12-18 11:00');
