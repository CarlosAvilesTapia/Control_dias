from flask import Blueprint, request, render_template, abort
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

dias_administrativos_bp = Blueprint('dias_administrativos', __name__)

# Límite máximo de días administrativos legales permitidos por año.
MAX_DIAS_LIBRES = 6.0

@dias_administrativos_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_dias_administrativos():
    message = None
    message_type = None
    empleado_id = current_user.id
    db = get_db()
    current_year = datetime.now().year

    # Calcular la cantidad de días ya solicitados en el año actual para este empleado
    cur = db.execute(
        """
        SELECT SUM(cantidad_dias) AS total 
        FROM dias_administrativos 
        WHERE empleado_id = ?
        AND strftime('%Y', fecha_solicitud) = ?
        AND estado = 'aprobado'
        """,
        (empleado_id, str(current_year))
    )
    row = cur.fetchone()
    total_dias_usados = float(row['total']) if row['total'] is not None else 0.0
    available_days = MAX_DIAS_LIBRES - total_dias_usados

    if request.method == 'POST':           
        try:
            cantidad_dias = float(request.form.get('cantidad_dias'))
        except (ValueError, TypeError):
            message = "¿Qué está haciendo? Ingrese la cantidad de días."
            message_type = "danger"
            return render_template('solicitar_dias_administrativos.html', 
                                   message=message, 
                                   message_type=message_type, 
                                   available_days=available_days)
        
        if cantidad_dias <= 0:
            message = "Pida un media día por lo menos ¿Para qué se metió acá?"
            message_type = "danger"
            return render_template('solicitar_dias_administrativos.html', 
                                   message=message, 
                                   message_type=message_type, 
                                   available_days=available_days)

        # Verificar que la nueva solicitud no exceda el máximo permitido.
        if total_dias_usados + cantidad_dias > MAX_DIAS_LIBRES:
            message = (
                f"¿Más de {MAX_DIAS_LIBRES:.1f} días por año? ¡Pare de gozar!. "
                f"Ha usado {total_dias_usados:.1f} días y está solicitando {cantidad_dias:.1f} días. Otsea."
            )
            message_type = "danger"
            return render_template('solicitar_dias_administrativos.html', 
                                   message=message, 
                                   message_type=message_type, 
                                   available_days=available_days)

        # Registrar la solicitud
        fecha_solicitud = datetime.now().strftime("%Y-%m-%d")
        db.execute(
            "INSERT INTO dias_administrativos (empleado_id, cantidad_dias, fecha_solicitud, estado) VALUES (?, ?, ?, ?)",
            (empleado_id, cantidad_dias, fecha_solicitud, 'pendiente')
        )
        db.commit()
        message = "Solicitud de días administrativos enviada. Vaya con dios."
        message_type = "success"

        # Actualizar el contador tras la inserción
        total_dias_usados += cantidad_dias
        available_days = MAX_DIAS_LIBRES - total_dias_usados

    return render_template('solicitar_dias_administrativos.html', 
                           message=message, 
                           message_type=message_type, 
                           available_days=available_days)
