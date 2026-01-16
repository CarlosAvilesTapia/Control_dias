import sqlite3
from flask import current_app, g
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, username, role, dias_vacaciones=0, activo=1):
        self.id = id
        self.username = username
        self.role = role
        self.dias_vacaciones = dias_vacaciones
        self.activo = activo

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

def create_request(user_id, request_type, start_date, end_date, days, reason=None, half_day_part=None):
    """
    Crea una solicitud en la tabla requests con estado 'pendiente'.
    """
    db = get_db()
    db.execute("""
        INSERT INTO requests (user_id, request_type, status, start_date, end_date, days, reason, half_day_part)
        VALUES (?, ?, 'pendiente', ?, ?, ?, ?, ?)
        """,
        (user_id, request_type, start_date, end_date, days, reason, half_day_part)
    )
    db.commit()

    return db.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_request_status(request_id, nuevo_estado, admin_comment=None):
    """
    Cambia el estado de una solicitud (pendiente/aprobada/rechazada).
    El comentario del admin es opcional.
    """
    db = get_db()
    db.execute("""
        UPDATE requests
        SET status = ?,
            admin_comment = COALESCE(?, admin_comment)
        WHERE id = ?
    """, (nuevo_estado, admin_comment, request_id))
    db.commit()
