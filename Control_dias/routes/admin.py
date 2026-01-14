from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime
from routes.vacaciones import contar_dias_habiles, feriados_chile

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/panel')
@login_required
def admin_panel():
    if current_user.role != 'administrador':
        abort(403)

    db = get_db()

    # Selector de año (por defecto: año actual)
    current_year = datetime.now().year
    selected_year = request.args.get('anio', type=int) or current_year

    # Lista de años disponibles (desde las tablas con anio)
    years_rows = db.execute("""
        SELECT DISTINCT anio FROM (
            SELECT anio FROM dias_administrativos
            UNION
            SELECT anio FROM vacaciones
            UNION
            SELECT anio FROM horas_extras
            UNION
            SELECT anio FROM horas_compensadas
        )
        WHERE anio IS NOT NULL
        ORDER BY anio DESC
    """).fetchall()
    available_years = [r['anio'] for r in years_rows] or [current_year]
    if selected_year not in available_years:
        # Si el año pedido no existe aún en data, igual lo permitimos
        # para que el admin pueda "mirar" un año sin registros.
        available_years = [selected_year] + available_years

    # —— DÍAS ADMINISTRATIVOS —— 
    pending_administrativos = db.execute("""
        SELECT da.id,
               da.cantidad_dias,
               da.fecha_solicitud,
               da.estado,
               da.anio,
               u.username
        FROM dias_administrativos da
        JOIN users u ON da.empleado_id = u.id
        WHERE da.estado = 'pendiente'
          AND da.anio = ?
        ORDER BY da.fecha_solicitud DESC
    """, (selected_year,)).fetchall()

    approved_administrativos = db.execute("""
        SELECT da.id,
               da.cantidad_dias,
               da.fecha_solicitud,
               da.estado,
               da.anio,
               u.username
        FROM dias_administrativos da
        JOIN users u ON da.empleado_id = u.id
        WHERE da.estado = 'aprobado'
          AND da.anio = ?
        ORDER BY da.fecha_solicitud DESC
    """, (selected_year,)).fetchall()

    # —— VACACIONES —— 
    vac_rows_pending = db.execute("""
        SELECT v.id,
               v.fecha_inicio,
               v.fecha_fin,
               v.estado,
               v.anio,
               u.username
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'pendiente'
          AND v.anio = ?
        ORDER BY v.fecha_inicio DESC
    """, (selected_year,)).fetchall()

    pending_vacaciones = []
    for row in vac_rows_pending:
        rec = dict(row)
        try:
            inicio = datetime.strptime(rec['fecha_inicio'], "%Y-%m-%d")
            fin    = datetime.strptime(rec['fecha_fin'],    "%Y-%m-%d")
            rec['dias_solicitados'] = contar_dias_habiles(inicio, fin, feriados_chile)
        except Exception:
            rec['dias_solicitados'] = 0
        pending_vacaciones.append(rec)

    vac_rows_approved = db.execute("""
        SELECT v.id,
               v.fecha_inicio,
               v.fecha_fin,
               v.estado,
               v.anio,
               u.username
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'aprobado'
          AND v.anio = ?
        ORDER BY v.fecha_inicio DESC
    """, (selected_year,)).fetchall()

    approved_vacaciones = []
    for row in vac_rows_approved:
        rec = dict(row)
        try:
            inicio = datetime.strptime(rec['fecha_inicio'], "%Y-%m-%d")
            fin    = datetime.strptime(rec['fecha_fin'],    "%Y-%m-%d")
            rec['dias_solicitados'] = contar_dias_habiles(inicio, fin, feriados_chile)
        except Exception:
            rec['dias_solicitados'] = 0
        approved_vacaciones.append(rec)

    # —— HORAS EXTRAS —— 
    pending_horas_extras = db.execute("""
        SELECT h.id,
               h.fecha,
               h.cantidad_horas,
               h.motivo,
               h.estado,
               h.anio,
               u.username
        FROM horas_extras h
        JOIN users u ON h.empleado_id = u.id
        WHERE h.estado = 'pendiente'
          AND h.anio = ?
        ORDER BY h.fecha DESC
    """, (selected_year,)).fetchall()

    approved_horas_extras = db.execute("""
        SELECT h.id,
               h.fecha,
               h.cantidad_horas,
               h.motivo,
               h.estado,
               h.anio,
               u.username
        FROM horas_extras h
        JOIN users u ON h.empleado_id = u.id
        WHERE h.estado = 'aprobado'
          AND h.anio = ?
        ORDER BY h.fecha DESC
    """, (selected_year,)).fetchall()

    # —— HORAS COMPENSADAS —— 
    pending_horas_compensadas = db.execute("""
        SELECT hc.id,
               hc.fecha_solicitud,
               hc.cantidad_horas,
               hc.estado,
               hc.anio,
               u.username
        FROM horas_compensadas hc
        JOIN users u ON hc.empleado_id = u.id
        WHERE hc.estado = 'pendiente'
          AND hc.anio = ?
        ORDER BY hc.fecha_solicitud DESC
    """, (selected_year,)).fetchall()

    approved_horas_compensadas = db.execute("""
        SELECT hc.id,
               hc.fecha_solicitud,
               hc.cantidad_horas,
               hc.estado,
               hc.anio,
               u.username
        FROM horas_compensadas hc
        JOIN users u ON hc.empleado_id = u.id
        WHERE hc.estado = 'aprobado'
          AND hc.anio = ?
        ORDER BY hc.fecha_solicitud DESC
    """, (selected_year,)).fetchall()

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

    modulo       = request.form['modulo']
    solicitud_id = request.form['solicitud_id']
    nuevo_estado = request.form['nuevo_estado']

    # Para volver al mismo año seleccionado tras actualizar
    selected_year = request.form.get('anio', type=int) or datetime.now().year

    if nuevo_estado not in ['aprobado', 'rechazado', 'pendiente']:
        flash("Estado inválido.", "error")
        return redirect(url_for('admin.admin_panel', anio=selected_year))

    db = get_db()

    # —— DÍAS ADMINISTRATIVOS —— 
    if modulo == 'dias_administrativos':
        db.execute(
            "UPDATE dias_administrativos SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # —— VACACIONES —— 
    elif modulo == 'vacaciones':
        sol = db.execute(
            "SELECT empleado_id, fecha_inicio, fecha_fin, cantidad_dias, anio FROM vacaciones WHERE id = ?",
            (solicitud_id,)
        ).fetchone()

        if not sol:
            flash("Solicitud no encontrada.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

        empleado_id = sol['empleado_id']
        dias_solicitados = int(sol['cantidad_dias'])
        anio_sol = int(sol['anio'])

        usr = db.execute(
            "SELECT dias_vacaciones FROM users WHERE id = ?",
            (empleado_id,)
        ).fetchone()
        asignadas = int(usr['dias_vacaciones'])

        used = db.execute("""
            SELECT COALESCE(SUM(cantidad_dias), 0) AS usadas
            FROM vacaciones
            WHERE empleado_id = ?
              AND estado = 'aprobado'
              AND anio = ?
        """, (empleado_id, anio_sol)).fetchone()['usadas']

        usadas = int(used)

        if nuevo_estado == 'aprobado' and usadas + dias_solicitados > asignadas:
            restantes = max(0, asignadas - usadas)
            flash(f"No puedes aprobar {dias_solicitados} días: solo quedan {restantes}.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

        db.execute(
            "UPDATE vacaciones SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # —— HORAS EXTRAS —— 
    elif modulo == 'horas_extras':
        sol_he = db.execute(
            "SELECT empleado_id, cantidad_horas, estado, anio FROM horas_extras WHERE id = ?",
            (solicitud_id,)
        ).fetchone()
        if not sol_he:
            flash("Solicitud de horas extras no encontrada.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

        empleado_id = sol_he['empleado_id']
        estado_anterior = sol_he['estado']
        anio_he = int(sol_he['anio'])

        if nuevo_estado in ['pendiente', 'rechazado'] and estado_anterior == 'aprobado':
            comp_count = db.execute(
                """
                SELECT COUNT(*) as cnt
                FROM horas_compensadas
                WHERE empleado_id = ?
                  AND estado = 'aprobado'
                  AND anio = ?
                """,
                (empleado_id, anio_he)
            ).fetchone()['cnt'] or 0

            if comp_count > 0:
                flash(
                    "No se puede restituir horas extras porque existen "
                    "horas compensadas aprobadas que dependen de ellas.",
                    "error"
                )
                return redirect(url_for('admin.admin_panel', anio=selected_year))

        db.execute(
            "UPDATE horas_extras SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # —— HORAS COMPENSADAS —— 
    elif modulo == 'horas_compensadas':
        sol_hc = db.execute(
            "SELECT empleado_id, cantidad_horas, estado, anio FROM horas_compensadas WHERE id = ?",
            (solicitud_id,)
        ).fetchone()
        if not sol_hc:
            flash("Solicitud de horas compensadas no encontrada.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

        empleado_id = sol_hc['empleado_id']
        hc_solicitadas = float(sol_hc['cantidad_horas'] or 0)
        estado_anterior_hc = sol_hc['estado']
        anio_hc = int(sol_hc['anio'])

        if nuevo_estado == 'aprobado':
            result_extras = db.execute(
                """
                SELECT COALESCE(SUM(cantidad_horas), 0) as total
                FROM horas_extras
                WHERE empleado_id = ?
                  AND estado = 'aprobado'
                  AND anio = ?
                """,
                (empleado_id, anio_hc)
            ).fetchone()
            total_extras = float(result_extras['total'] or 0)

            result_comp = db.execute(
                """
                SELECT COALESCE(SUM(cantidad_horas), 0) as total
                FROM horas_compensadas
                WHERE empleado_id = ?
                  AND estado = 'aprobado'
                  AND anio = ?
                  AND id <> ?
                """,
                (empleado_id, anio_hc, solicitud_id)
            ).fetchone()
            total_comp_otros = float(result_comp['total'] or 0)

            disponibles_horas = total_extras - total_comp_otros
            if hc_solicitadas > disponibles_horas:
                flash(
                    f"No puedes aprobar {hc_solicitadas:.1f} horas compensadas: "
                    f"solo quedan {disponibles_horas:.1f} horas extras disponibles.",
                    "error"
                )
                return redirect(url_for('admin.admin_panel', anio=selected_year))

            db.execute(
                "UPDATE horas_compensadas SET estado = ? WHERE id = ?",
                (nuevo_estado, solicitud_id)
            )

        elif nuevo_estado in ['pendiente', 'rechazado']:
            db.execute(
                "UPDATE horas_compensadas SET estado = ? WHERE id = ?",
                (nuevo_estado, solicitud_id)
            )
        else:
            flash("Estado inválido para horas compensadas.", "error")
            return redirect(url_for('admin.admin_panel', anio=selected_year))

    else:
        flash("Módulo desconocido.", "error")
        return redirect(url_for('admin.admin_panel', anio=selected_year))

    db.commit()
    flash("Estado actualizado correctamente.", "success")
    return redirect(url_for('admin.admin_panel', anio=selected_year))
