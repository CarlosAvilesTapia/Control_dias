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

    # —— DÍAS ADMINISTRATIVOS —— 
    pending_administrativos = db.execute("""
        SELECT da.id,
               da.cantidad_dias,
               da.fecha_solicitud,
               da.estado,
               u.username
        FROM dias_administrativos da
        JOIN users u ON da.empleado_id = u.id
        WHERE da.estado = 'pendiente'
    """).fetchall()

    approved_administrativos = db.execute("""
        SELECT da.id,
               da.cantidad_dias,
               da.fecha_solicitud,
               da.estado,
               u.username
        FROM dias_administrativos da
        JOIN users u ON da.empleado_id = u.id
        WHERE da.estado = 'aprobado'
    """).fetchall()

    # —— VACACIONES —— 
    vac_rows_pending = db.execute("""
        SELECT v.id,
               v.fecha_inicio,
               v.fecha_fin,
               v.estado,
               u.username
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'pendiente'
    """).fetchall()

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
               u.username
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'aprobado'
    """).fetchall()

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
               u.username
        FROM horas_extras h
        JOIN users u ON h.empleado_id = u.id
        WHERE h.estado = 'pendiente'
    """).fetchall()

    approved_horas_extras = db.execute("""
        SELECT h.id,
               h.fecha,
               h.cantidad_horas,
               h.motivo,
               h.estado,
               u.username
        FROM horas_extras h
        JOIN users u ON h.empleado_id = u.id
        WHERE h.estado = 'aprobado'
    """).fetchall()

    # —— HORAS COMPENSADAS —— 
    pending_horas_compensadas = db.execute("""
        SELECT hc.id,
               hc.fecha_solicitud,
               hc.cantidad_horas,
               hc.estado,
               u.username
        FROM horas_compensadas hc
        JOIN users u ON hc.empleado_id = u.id
        WHERE hc.estado = 'pendiente'
    """).fetchall()

    approved_horas_compensadas = db.execute("""
        SELECT hc.id,
               hc.fecha_solicitud,
               hc.cantidad_horas,
               hc.estado,
               u.username
        FROM horas_compensadas hc
        JOIN users u ON hc.empleado_id = u.id
        WHERE hc.estado = 'aprobado'
    """).fetchall()

    return render_template(
        'admin_panel.html',
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

    if nuevo_estado not in ['aprobado', 'rechazado', 'pendiente']:
        flash("Estado inválido.", "error")
        return redirect(url_for('admin.admin_panel'))

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
            "SELECT empleado_id, fecha_inicio, fecha_fin FROM vacaciones WHERE id = ?",
            (solicitud_id,)
        ).fetchone()
        if not sol:
            flash("Solicitud no encontrada.", "error")
            return redirect(url_for('admin.admin_panel'))

        empleado_id = sol['empleado_id']
        inicio = datetime.strptime(sol['fecha_inicio'], "%Y-%m-%d")
        fin    = datetime.strptime(sol['fecha_fin'],    "%Y-%m-%d")
        dias_solicitados = contar_dias_habiles(inicio, fin, feriados_chile)

        usr = db.execute(
            "SELECT dias_vacaciones FROM users WHERE id = ?",
            (empleado_id,)
        ).fetchone()
        asignadas = int(usr['dias_vacaciones'])

        used = db.execute("""
            SELECT SUM(JULIANDAY(fecha_fin)-JULIANDAY(fecha_inicio)+1) AS usadas
            FROM vacaciones
            WHERE empleado_id = ? AND estado = 'aprobado'
        """, (empleado_id,)).fetchone()['usadas'] or 0
        usadas = int(used)

        # Si intentan aprobar, validamos cupo
        if nuevo_estado == 'aprobado' and usadas + dias_solicitados > asignadas:
            restantes = max(0, asignadas - usadas)
            flash(f"No puedes aprobar {dias_solicitados} días: solo quedan {restantes}.", "error")
            return redirect(url_for('admin.admin_panel'))

        # Sea aprobar, rechazar o devolver a pendiente, solo actualizamos
        db.execute(
            "UPDATE vacaciones SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # —— HORAS EXTRAS —— 
    elif modulo == 'horas_extras':
        sol_he = db.execute(
            "SELECT empleado_id, cantidad_horas, estado FROM horas_extras WHERE id = ?",
            (solicitud_id,)
        ).fetchone()
        if not sol_he:
            flash("Solicitud de horas extras no encontrada.", "error")
            return redirect(url_for('admin.admin_panel'))

        empleado_id = sol_he['empleado_id']
        estado_anterior = sol_he['estado']

        # Si vienen a restituir (pendiente/rechazado) una hora extra previamente aprobada,
        # deben asegurarse de no dejar horas compensadas aprobadas sin respaldo.
        if nuevo_estado in ['pendiente', 'rechazado'] and estado_anterior == 'aprobado':
            comp_count = db.execute(
                "SELECT COUNT(*) as cnt FROM horas_compensadas "
                "WHERE empleado_id = ? AND estado = 'aprobado'",
                (empleado_id,)
            ).fetchone()['cnt'] or 0

            if comp_count > 0:
                flash(
                    "No se puede restituir horas extras porque existen "
                    "horas compensadas aprobadas que dependen de ellas.",
                    "error"
                )
                return redirect(url_for('admin.admin_panel'))

        # Actualizamos el estado (aprobado, rechazado o pendiente)
        db.execute(
            "UPDATE horas_extras SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # —— HORAS COMPENSADAS —— 
    elif modulo == 'horas_compensadas':
        sol_hc = db.execute(
            "SELECT empleado_id, cantidad_horas, estado FROM horas_compensadas WHERE id = ?",
            (solicitud_id,)
        ).fetchone()
        if not sol_hc:
            flash("Solicitud de horas compensadas no encontrada.", "error")
            return redirect(url_for('admin.admin_panel'))

        empleado_id = sol_hc['empleado_id']
        hc_solicitadas = float(sol_hc['cantidad_horas'] or 0)
        estado_anterior_hc = sol_hc['estado']

        if nuevo_estado == 'aprobado':
            # Valida que no se exceda de horas extras aprobadas
            result_extras = db.execute(
                "SELECT SUM(cantidad_horas) as total "
                "FROM horas_extras "
                "WHERE empleado_id = ? AND estado = 'aprobado'",
                (empleado_id,)
            ).fetchone()
            total_extras = float(result_extras['total'] or 0)

            result_comp = db.execute(
                "SELECT SUM(cantidad_horas) as total "
                "FROM horas_compensadas "
                "WHERE empleado_id = ? AND estado = 'aprobado' AND id <> ?",
                (empleado_id, solicitud_id)
            ).fetchone()
            total_comp_otros = float(result_comp['total'] or 0)

            disponibles_horas = total_extras - total_comp_otros
            if hc_solicitadas > disponibles_horas:
                flash(
                    f"No puedes aprobar {hc_solicitadas:.1f} horas compensadas: "
                    f"solo quedan {disponibles_horas:.1f} horas extras disponibles.",
                    "error"
                )
                return redirect(url_for('admin.admin_panel'))

            db.execute(
                "UPDATE horas_compensadas SET estado = ? WHERE id = ?",
                (nuevo_estado, solicitud_id)
            )

        elif nuevo_estado in ['pendiente', 'rechazado']:
            # Ya no bloqueamos si no hay horas extras; simplemente actualizamos
            db.execute(
                "UPDATE horas_compensadas SET estado = ? WHERE id = ?",
                (nuevo_estado, solicitud_id)
            )

        else:
            flash("Estado inválido para horas compensadas.", "error")
            return redirect(url_for('admin.admin_panel'))

    else:
        flash("Módulo desconocido.", "error")
        return redirect(url_for('admin.admin_panel'))

    db.commit()
    flash("Estado actualizado correctamente.", "success")
    return redirect(url_for('admin.admin_panel'))
