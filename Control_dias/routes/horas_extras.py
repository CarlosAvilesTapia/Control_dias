from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

horas_extras_bp = Blueprint('horas_extras', __name__)

@horas_extras_bp.route('/reportar', methods=['GET', 'POST'])
@login_required
def reportar_horas_extras():
    message = None
    empleado_id = current_user.id
    if request.method == 'POST':        
        fecha = request.form.get('fecha')
        try:
            cantidad_horas = float(request.form.get('cantidad_horas'))
        except (ValueError, TypeError):
            message = "¿Qué está haciendo? Ingrese la cantidad de horas."
            return render_template('reportar_horas_extras.html', message=message)
        
        motivo = request.form.get('motivo')

        if not fecha or cantidad_horas <= 0 or not motivo:
            message = "Por favor, haga el reporte como se debe."
            return render_template('reportar_horas_extras.html', message=message)
        
        # Verificación si las horas son dobles.
        if request.form.get('doblar'):
            cantidad_horas *= 2

        # Conexión a la base de datos.
        db = get_db()
        db.execute(
            "INSERT INTO horas_extras (empleado_id, fecha, cantidad_horas, motivo, estado) VALUES (?, ?, ?, ?, ?)",
            (empleado_id, fecha, cantidad_horas, motivo, 'pendiente')
        )
        db.commit()
        message = "Horas extras reportadas exitosamente ¡Muchas gracias por su esfuerzo!"
    
    return render_template('reportar_horas_extras.html', message=message)

# Nueva ruta para solicitar horas compensadas (convertir horas extras en tiempo libre)
@horas_extras_bp.route('/solicitar_compensadas', methods=['GET', 'POST'])
@login_required
def solicitar_horas_compensadas():
    message = None
    empleado_id = current_user.id
    db = get_db()
    
    # Calcular cuántas horas extra aprobadas tiene el usuario.
    # Esta consulta asume que las horas extras "aprobadas" están registradas en la tabla horas_extras.
    # Total de horas extras aprobadas
    result_extra = db.execute(
        "SELECT SUM(cantidad_horas) as total FROM horas_extras WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    total_extras_aprobadas = result_extra['total'] if result_extra['total'] is not None else 0

    # Total de horas compensadas ya aprobadas
    result_compensadas = db.execute(
        "SELECT SUM(cantidad_horas) as total FROM horas_compensadas WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    total_compensadas = result_compensadas['total'] if result_compensadas['total'] is not None else 0

    # Horas disponibles = aprobadas - compensadas
    available_hours = total_extras_aprobadas - total_compensadas 

    if request.method == 'POST':
        try:
            requested_hours = float(request.form.get('cantidad_horas'))
        except (ValueError, TypeError):
            message = "¿Qué está haciendo? Ingrese la cantidad de horas que quiere solicitar."
            return render_template('solicitar_horas_compensadas.html', message=message, available_hours=available_hours)
        
        if requested_hours <= 0:
            message = "Pida una hora por lo menos ¿Para qué se metió acá?"
            return render_template('solicitar_horas_compensadas.html', message=message, available_hours=available_hours)
        
        if requested_hours > available_hours:
            message = f"Parece que no se ha puesto la camiseta. Solo tiene disponibles: {available_hours} horas."
            return render_template('solicitar_horas_compensadas.html', message=message, available_hours=available_hours)
        
        # Registrar la solicitud de horas compensadas con estado "pendiente"
        fecha_solicitud = datetime.now().strftime("%Y-%m-%d")
        db.execute(
            "INSERT INTO horas_compensadas (empleado_id, cantidad_horas, fecha_solicitud, estado) VALUES (?, ?, ?, ?)",
            (empleado_id, requested_hours, fecha_solicitud, 'pendiente')
        )
        db.commit()
        message = "Solicitud de horas compensadas enviada. Vaya con dios."
    
    return render_template('solicitar_horas_compensadas.html', message=message, available_hours=available_hours)
