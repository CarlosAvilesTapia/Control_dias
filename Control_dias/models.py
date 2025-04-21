import sqlite3
from flask import current_app, g
from werkzeug.security import generate_password_hash, check_password_hash

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

def get_user_by_username(username):
    """Obtiene un usuario por su nombre de usuario."""
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return user

def create_user(username, password, role='empleado', dias_vacaciones=15):
    """Crea un nuevo usuario con el rol especificado (por defecto 'empleado')."""
    db = get_db()
    password_hash = generate_password_hash(password)
    db.execute("INSERT INTO users (username, password_hash, role, dias_vacaciones) VALUES (?, ?, ?, ?)",
               (username, password_hash, role, dias_vacaciones))
    db.commit()

def verify_password(user, password):
    """Verifica que la contraseña proporcionada coincide con el hash almacenado."""
    return check_password_hash(user['password_hash'], password)
