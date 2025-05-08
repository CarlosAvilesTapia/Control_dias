from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime
from routes.vacaciones import contar_dias_habiles, feriados_chile

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/panel')  
@login_required
def admin_panel():
    # Sólo el admin puede entrar
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

    # —— VACACIONES ——
    # Traemos las solicitudes con fechas crudas
    vac_rows = db.execute("""
        SELECT v.id,
               v.fecha_inicio,
               v.fecha_fin,
               v.estado,
               u.username
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'pendiente'
    """).fetchall()

    # Convertimos a dict y calculamos días hábiles
    pending_vacaciones = []
    for row in vac_rows:
        rec = dict(row)
        try:
            inicio = datetime.strptime(rec['fecha_inicio'], "%Y-%m-%d")
            fin    = datetime.strptime(rec['fecha_fin'],    "%Y-%m-%d")
            rec['dias_solicitados'] = contar_dias_habiles(inicio, fin, feriados_chile)
        except Exception:
            rec['dias_solicitados'] = 0
        pending_vacaciones.append(rec)

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

    return render_template(
        'admin_panel.html',
        pending_administrativos=pending_administrativos,
        pending_vacaciones=pending_vacaciones,
        pending_horas_extras=pending_horas_extras,
        pending_horas_compensadas=pending_horas_compensadas
    )

@admin_bp.route('/actualizar_estado', methods=['POST'])
@login_required
def actualizar_estado():
    if current_user.role != 'administrador':
        abort(403)

    modulo       = request.form['modulo']
    solicitud_id = request.form['solicitud_id']
    nuevo_estado = request.form['nuevo_estado']

    if nuevo_estado not in ['aprobado', 'rechazado']:
        flash("Estado inválido.", "error")
        return redirect(url_for('admin.admin_panel'))

    db = get_db()

    # (Ejemplo de validación de vacaciones; deja el resto igual)
    if modulo == 'vacaciones':
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

        # días asignados al usuario
        usr = db.execute(
            "SELECT dias_vacaciones FROM users WHERE id = ?",
            (empleado_id,)
        ).fetchone()
        asignadas = int(usr['dias_vacaciones'])

        # días ya usados
        used = db.execute("""
            SELECT SUM(JULIANDAY(fecha_fin)-JULIANDAY(fecha_inicio)+1) AS usadas
            FROM vacaciones
            WHERE empleado_id = ? AND estado = 'aprobado'
        """, (empleado_id,)).fetchone()['usadas'] or 0
        usadas = int(used)

        # Validación de cupo
        if nuevo_estado == 'aprobado' and usadas + dias_solicitados > asignadas:
            restantes = max(0, asignadas - usadas)
            flash(f"No puedes aprobar {dias_solicitados} días: solo quedan {restantes}.", "error")
            return redirect(url_for('admin.admin_panel'))

        db.execute(
            "UPDATE vacaciones SET estado = ? WHERE id = ?",
            (nuevo_estado, solicitud_id)
        )

    # para los demás módulos simplemente actualiza
    elif modulo == 'dias_administrativos':
        db.execute("UPDATE dias_administrativos SET estado = ? WHERE id = ?",
                   (nuevo_estado, solicitud_id))
    elif modulo == 'horas_extras':
        db.execute("UPDATE horas_extras SET estado = ? WHERE id = ?",
                   (nuevo_estado, solicitud_id))
    elif modulo == 'horas_compensadas':
        db.execute("UPDATE horas_compensadas SET estado = ? WHERE id = ?",
                   (nuevo_estado, solicitud_id))
    else:
        flash("Módulo desconocido.", "error")
        return redirect(url_for('admin.admin_panel'))

    db.commit()
    flash("Estado actualizado correctamente.", "success")
    return redirect(url_for('admin.admin_panel'))
