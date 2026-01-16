-- Tabla para solicitudes de vacaciones
CREATE TABLE IF NOT EXISTS vacaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    cantidad_dias REAL NOT NULL,
    estado TEXT NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (empleado_id) REFERENCES users(id)
);

-- Tabla para reporte de horas extras
CREATE TABLE IF NOT EXISTS horas_extras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    cantidad_horas REAL NOT NULL,
    motivo TEXT NOT NULL,
    estado TEXT NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (empleado_id) REFERENCES users(id)
);

-- Crear la tabla dias_administrativos si no existe
CREATE TABLE IF NOT EXISTS dias_administrativos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    cantidad_dias REAL NOT NULL,
    fecha_solicitud TEXT NOT NULL,
    estado TEXT NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (empleado_id) REFERENCES users(id)
);

-- Crear tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    dias_vacaciones INTEGER NOT NULL DEFAULT 0
);

-- Crear tabla de horas compensadas
CREATE TABLE IF NOT EXISTS horas_compensadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    cantidad_horas REAL NOT NULL,
    fecha_solicitud TEXT NOT NULL,
    estado TEXT NOT NULL,
    anio INTEGER NOT NULL,
    FOREIGN KEY (empleado_id) REFERENCES users(id)
);

-- Tabla para mostrar solicitudes
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    request_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendiente',
    start_date TEXT,
    end_date TEXT,
    days REAL,
    reason TEXT,
    admin_comment TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT,
    reviewed_by INTEGER,
    reviewed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (reviewed_by) REFERENCES users (id)
);
