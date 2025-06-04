-- Tabla para solicitudes de vacaciones
CREATE TABLE IF NOT EXISTS vacaciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    estado TEXT NOT NULL
);

-- Tabla para reporte de horas extras
CREATE TABLE IF NOT EXISTS horas_extras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    fecha TEXT NOT NULL,
    cantidad_horas REAL NOT NULL,
    motivo TEXT NOT NULL,
    estado TEXT NOT NULL
);

-- Crear la tabla dias_administrativos si no existe
CREATE TABLE IF NOT EXISTS dias_administrativos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id TEXT NOT NULL,
    cantidad_dias REAL NOT NULL,
    fecha_solicitud TEXT NOT NULL,
    estado TEXT NOT NULL
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
    estado TEXT NOT NULL
);