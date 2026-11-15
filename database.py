import sqlite3
import hashlib

DB = "land.db"


def get_conn():
    return sqlite3.connect(DB)


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user')""")
    c.execute("""CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        survey_no TEXT UNIQUE NOT NULL,
        owner TEXT NOT NULL,
        village TEXT,
        area_sqft REAL,
        latitude REAL,
        longitude REAL)""")
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?,?,?)",
              ("admin", hash_pw("admin123"), "admin"))
    conn.commit()
    conn.close()


def register_user(username, password):
    try:
        conn = get_conn()
        conn.execute("INSERT INTO users (username, password) VALUES (?,?)",
                     (username, hash_pw(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def check_login(username, password):
    conn = get_conn()
    row = conn.execute("SELECT role FROM users WHERE username=? AND password=?",
                       (username, hash_pw(password))).fetchone()
    conn.close()
    return row[0] if row else None


def add_land(survey_no, owner, village, area, lat, lon):
    try:
        conn = get_conn()
        conn.execute("""INSERT INTO lands (survey_no, owner, village, area_sqft, latitude, longitude)
                        VALUES (?,?,?,?,?,?)""",
                     (survey_no, owner, village, area, lat, lon))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def get_lands():
    conn = get_conn()
    rows = conn.execute("SELECT survey_no, owner, village, area_sqft, latitude, longitude FROM lands").fetchall()
    conn.close()
    return rows