from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

from routes.vacaciones import contar_dias_habiles, feriados_chile  # opcional, para fallback

admin_bp = Blueprint('admin', __name__)

# Mapeo para compatibilidad con tu formulario actual (aprobado/rechazado)
MAP_ESTADOS = {
    "pendiente": "pendiente",
    "aprobado": "aprobada",
    "rechazado": "rechazada",
    # por si en alguna parte ya llega en femenino
    "aprobada": "aprobada",
    "rechazada": "rechazada",
}

TIPOS = {
    "dias_administrativos": "administrativo",
    "vacaciones": "vacaciones",
    "horas_extras": "horas_extras",
    "horas_compensadas": "horas_compensadas",
}

def _anio_desde_start_date(start_date: str):
    # start_date viene como 'YYYY-MM-DD'
    if not start_date or len(start_date) < 4:
        return None
    try:
        return int(start_date[:4])
    except Exception:
        return None


@admin_bp.route('/panel')
@login_required
def admin_panel():
    if current_user.role != 'administrador':
        abort(403)

    db = get_db()

    current_year = datetime.now().year
    selected_year = request.args.get('anio', type=int) or current_year

    # Años disponibles desde requests (derivados de start_date)
    years_rows = db.execute("""
        SELECT DISTINCT CAST(substr(start_date, 1, 4) AS INTEGER) AS anio
        FROM requests
        WHERE start_date IS NOT NULL
          AND length(start_date) >= 4
        ORDER BY anio DESC
    """).fetchall()

    available_years = [r['anio'] for r in years_rows if r['anio'] is not None]
    if not available_years:
        available_years = [current_year]

    # si el año pedido no está disponible, cae al más reciente disponible
    if selected_year not in available_years:
        selected_year = available_years[0]

    # Helper para traer solicitudes por tipo/estado/año
    def traer_solicitudes(request_type, status, year):
        # Filtramos por año usando start_date
        return db.execute("""
            SELECT r.id,
                   r.user_id,
                   r.request_type,
                   r.start_date,
                   r.end_date,
                   r.days,
                   r.reason,
                   r.status,
                   r.admin_comment,
                   r.created_at,
                   u.username
            FROM requests r
            JOIN users u ON r.user_id = u.id
            WHERE r.request_type = ?
              AND r.status = ?
              AND r.start_date IS NOT NULL
              AND substr(r.start_date, 1, 4) = ?
            ORDER BY r.start_date DESC, r.id DESC
        """, (request_type, status, str(year))).fetchall()

    # --- DÍAS ADMINISTRATIVOS ---
    pending_administrativos = traer_solicitudes("administrativo", "pendiente", selected_year)
    approved_administrativos = traer_solicitudes("administrativo", "aprobada", selected_year)

    # --- VACACIONES ---
    # Aquí, days debería venir ya calculado al solicitar. Si por alguna razón viene None, hacemos fallback.
    pending_vac_rows = traer_solicitudes("vacaciones", "pendiente", selected_year)
    pending_vacaciones = []
    for row in pending_vac_rows:
        rec = dict(row)
        if rec.get("days") is None and rec.get("start_date") and rec.get("end_date"):
            try:
                inicio = datetime.strptime(rec["start_date"], "%Y-%m-%d")
                fin = datetime.strptime(rec["end_date"], "%Y-%m-%d")
                rec["dias_solicitados"] = contar_dias_habiles(inicio, fin, feriados_chile)
            except Exception:
                rec["dias_solicitados"] = 0
        else:
            rec["dias_solicitados"] = int(rec["days"] or 0)
        pending_vacaciones.append(rec)

    approved_vac_rows = traer_solicitudes("vacaciones", "aprobada", selected_year)
    approved_vacaciones = []
    for row in approved_vac_rows:
        rec = dict(row)
        rec["dias_solicitados"] = int(rec["days"] or 0)
        approved_vacaciones.append(rec)

    # --- HORAS EXTRAS ---
    pending_horas_extras = traer_solicitudes("horas_extras", "pendiente", selected_year)
    approved_horas_extras = traer_solicitudes("horas_extras", "aprobada", selected_year)

    # --- HORAS COMPENSADAS ---
    pending_horas_compensadas = traer_solicitudes("horas_compensadas", "pendiente", selected_year)
    approved_horas_compensadas = traer_solicitudes("horas_compensadas", "aprobada", selected_year)

    return render_template(
        'admin_panel.html',
        selected_year=selected_year,
        available_years=available_years,
        pending_administrativos=pending_administrativos,
        approved_administrativos=approved_administrativos,
        pending_vacaciones=pending_vacaciones,
        approved_vacaciones=approved_vacaciones,
        pending_horas_extras=pending_horas_extras,
        approved_horas_extras=approved_horas_extras,
        pending_horas_compensadas=pending_horas_compensadas,
        approved_horas_compensadas=approved_horas_compensadas
    )


@admin_bp.route('/actualizar_estado', methods=['POST'])
@login_required
def actualizar_estado():
    if current_user.role != 'administrador':
        abort(403)

    modulo = request.form.get('modulo')  # mantenemos compatibilidad con tu form actual
    solicitud_id = request.form.get('solicitud_id')
    nuevo_estado_raw = request.form.get('nuevo_estado')

    raw = request.form.get('anio')
    try:
        selected_year = int(raw) if raw else datetime.now().year
    except ValueError:
        selected_year = datetime.now().year


    if not solicitud_id or not nuevo_estado_raw:
        flash("Faltan datos para actualizar el estado.", "error")
        return redirect(url_for('admin.admin_panel', anio=selected_year))

    # Mapear estados del form al estándar de requests
    nuevo_estado = MAP_ESTADOS.get(nuevo_estado_raw)
    if nuevo_estado not in ['aprobada', 'rechazada', 'pendiente']:
        flash("Estado inválido.", "error")
        return redirect(url_for('admin.admin_panel', anio=selected_year))

    db = get_db()

    # Determinar request_type esperado según "modulo" (si viene)
    request_type_esperado = None
    if modulo in TIPOS:
        request_type_esperado = TIPOS[modulo]

    # Cargar solicitud desde requests
    if request_type_esperado:
        sol = db.execute("""
            SELECT r.*, u.dias_vacaciones, u.username
            FROM requests r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = ? AND r.request_type = ?
        """, (solicitud_id, request_type_esperado)).fetchone()
    else:
        # fallback: si el form no manda modulo, igual buscamos por id
        sol = db.execute("""
            SELECT r.*, u.dias_vacaciones, u.username
            FROM requests r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = ?
        """, (solicitud_id,)).fetchone()

    if not sol:
        flash("Solicitud no encontrada.", "error")
        return redirect(url_for('admin.admin_panel', anio=selected_year))

    request_type = sol["request_type"]
    user_id = sol["user_id"]
    estado_anterior = sol["status"]
    anio_sol = _anio_desde_start_date(sol["start_date"]) or selected_year

    # --- Validaciones por tipo ---
    # VACACIONES: no aprobar si supera días asignados
    if request_type == "vacaciones" and nuevo_estado == "aprobada":
        asignadas = int(sol["dias_vacaciones"] or 0)
        dias_solicitados = int(sol["days"] or 0)

        usadas_row = db.execute("""
            SELECT COALESCE(SUM(days), 0) AS usadas
            FROM requests
            WHERE user_id = ?
              AND request_type = 'vacaciones'
              AND status = 'aprobada'
              AND substr(start_date, 1, 4) = ?
              AND id <> ?
        """, (user_id, str(anio_sol), sol["id"])).fetchone()
        usadas = int(usadas_row["usadas"] or 0)

        if usadas + dias_solicitados > asignadas:
            restantes = max(0, asignadas - usadas)
            flash(f"No puedes aprobar {dias_solicitados} días: solo quedan {restantes}.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

    # HORAS EXTRAS: si se intenta "des-aprobar" y existen compensadas aprobadas, bloquear
    if request_type == "horas_extras":
        if nuevo_estado in ["pendiente", "rechazada"] and estado_anterior == "aprobada":
            comp_count_row = db.execute("""
                SELECT COUNT(*) AS cnt
                FROM requests
                WHERE user_id = ?
                  AND request_type = 'horas_compensadas'
                  AND status = 'aprobada'
                  AND substr(start_date, 1, 4) = ?
            """, (user_id, str(anio_sol))).fetchone()
            comp_count = int(comp_count_row["cnt"] or 0)
            if comp_count > 0:
                flash(
                    "No se puede restituir horas extras porque existen horas compensadas aprobadas que dependen de ellas.",
                    "error"
                )
                return redirect(url_for('admin.admin_panel', anio=selected_year))

    # HORAS COMPENSADAS: al aprobar, validar disponibilidad contra horas extras aprobadas
    if request_type == "horas_compensadas" and nuevo_estado == "aprobada":
        hc_solicitadas = float(sol["days"] or 0)

        total_extras_row = db.execute("""
            SELECT COALESCE(SUM(days), 0) AS total
            FROM requests
            WHERE user_id = ?
              AND request_type = 'horas_extras'
              AND status = 'aprobada'
              AND substr(start_date, 1, 4) = ?
        """, (user_id, str(anio_sol))).fetchone()
        total_extras = float(total_extras_row["total"] or 0)

        total_comp_otros_row = db.execute("""
            SELECT COALESCE(SUM(days), 0) AS total
            FROM requests
            WHERE user_id = ?
              AND request_type = 'horas_compensadas'
              AND status = 'aprobada'
              AND substr(start_date, 1, 4) = ?
              AND id <> ?
        """, (user_id, str(anio_sol), sol["id"])).fetchone()
        total_comp_otros = float(total_comp_otros_row["total"] or 0)

        disponibles_horas = total_extras - total_comp_otros
        if hc_solicitadas > disponibles_horas:
            flash(
                f"No puedes aprobar {hc_solicitadas:.1f} horas compensadas: "
                f"solo quedan {disponibles_horas:.1f} horas extras disponibles.",
                "error"
            )
            return redirect(url_for('admin.admin_panel', anio=selected_year))

    # --- Actualizar estado en requests ---
    db.execute("""
        UPDATE requests
        SET status = ?,
            reviewed_by = ?,
            reviewed_at = datetime('now'),
            updated_at = datetime('now')
        WHERE id = ?
    """, (nuevo_estado, current_user.id, sol["id"]))

    db.commit()
    flash("Estado actualizado correctamente.", "success")
    return redirect(url_for('admin.admin_panel', anio=selected_year))
