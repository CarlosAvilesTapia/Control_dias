from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime
from routes.vacaciones import contar_dias_habiles, feriados_chile

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/panel')
@login_required
def admin_panel():
    # Solo el administrador puede acceder a este panel.
    if current_user.role != 'administrador':
        abort(403)
    
    db = get_db()
    # Consultar las solicitudes pendientes en cada módulo.
    pending_administrativos = db.execute("""
        SELECT da.id, da.cantidad_dias, da.fecha_solicitud, da.estado, u.username
        FROM dias_administrativos da
        JOIN users u ON da.empleado_id = u.id
        WHERE da.estado = 'pendiente'
    """).fetchall()

    
    pending_vacaciones = db.execute("""
        SELECT v.id, v.fecha_inicio, v.fecha_fin, v.estado, u.username,
               CAST(JULIANDAY(v.fecha_fin) - JULIANDAY(v.fecha_inicio) + 1 AS INTEGER) AS dias_solicitados
        FROM vacaciones v
        JOIN users u ON v.empleado_id = u.id
        WHERE v.estado = 'pendiente'
    """).fetchall()

    # Convertir los rows en diccionarios y agregar el cálculo de días solicitados excluyendo feriados y fines de semana
    pending_vacaciones_list = []
    for solicitud in pending_vacaciones:
        solicitud_dict = dict(solicitud)
        try:
            inicio = datetime.strptime(solicitud_dict['fecha_inicio'], "%Y-%m-%d")
            fin = datetime.strptime(solicitud_dict['fecha_fin'], "%Y-%m-%d")
            # Suponiendo que 'feriados_chile' y 'contar_dias_habiles' están importados desde vacaciones.py
            solicitud_dict['dias_solicitados'] = contar_dias_habiles(inicio, fin, feriados_chile)
        except Exception as e:
            solicitud_dict['dias_solicitados'] = 0
        pending_vacaciones_list.append(solicitud_dict)

    
    pending_horas_extras = db.execute("""
        SELECT h.id, h.fecha, h.cantidad_horas, h.motivo, h.estado, u.username
        FROM horas_extras h
        JOIN users u ON h.empleado_id = u.id
        WHERE h.estado = 'pendiente'
    """).fetchall()


    pending_horas_compensadas = db.execute("""
        SELECT hc.id, hc.fecha_solicitud, hc.cantidad_horas, hc.estado, u.username
        FROM horas_compensadas hc
        JOIN users u ON hc.empleado_id = u.id
        WHERE hc.estado = 'pendiente'
    """).fetchall()


    return render_template(
        'admin_panel.html',
        pending_administrativos=pending_administrativos,
        pending_vacaciones=pending_vacaciones_list,
        pending_horas_extras=pending_horas_extras,
        pending_horas_compensadas=pending_horas_compensadas
    )

@admin_bp.route('/actualizar_estado', methods=['POST'])
@login_required
def actualizar_estado():
    # Solo administradores pueden actualizar el estado.
    if current_user.role != 'administrador':
        abort(403)
    
    modulo = request.form.get('modulo')  # 'dias_administrativos', 'vacaciones' o 'horas_extras'
    solicitud_id = request.form.get('solicitud_id')
    nuevo_estado = request.form.get('nuevo_estado')
    
    # Validar el nuevo estado.
    if nuevo_estado not in ['aprobado', 'rechazado']:
        flash("Estado inválido.", "error")
        return redirect(url_for('admin.admin_panel'))
    
    db = get_db()
    if modulo == 'dias_administrativos':
        db.execute("UPDATE dias_administrativos SET estado = ? WHERE id = ?", (nuevo_estado, solicitud_id))
    elif modulo == 'vacaciones':
        db.execute("UPDATE vacaciones SET estado = ? WHERE id = ?", (nuevo_estado, solicitud_id))
    elif modulo == 'horas_extras':
        db.execute("UPDATE horas_extras SET estado = ? WHERE id = ?", (nuevo_estado, solicitud_id))
    elif modulo == 'horas_compensadas':
        db.execute("UPDATE horas_compensadas SET estado = ? WHERE id = ?", (nuevo_estado, solicitud_id))    
    else:
        flash("Módulo desconocido.", "error")
        return redirect(url_for('admin.admin_panel'))
    
    db.commit()
    flash("El estado se actualizó correctamente.", "success")
    return redirect(url_for('admin.admin_panel'))
