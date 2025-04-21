from flask import Blueprint, request, render_template, abort
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

dias_administrativos_bp = Blueprint('dias_administrativos', __name__)

# Límite máximo de días administrativos legales permitidos por año.
MAX_DIAS_LIBRES = 6

@dias_administrativos_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_dias_administrativos():
    message = None
    empleado_id = current_user.id
    db = get_db()
    current_year = datetime.now().year

    # Calcular la cantidad de días ya solicitados en el año actual para este empleado
    cur = db.execute(
        "SELECT SUM(cantidad_dias) AS total FROM dias_administrativos WHERE empleado_id = ? AND strftime('%Y', fecha_solicitud) = ?",
        (empleado_id, str(current_year))
    )
    row = cur.fetchone()
    total_dias_usados = row['total'] if row['total'] is not None else 0
    available_days = MAX_DIAS_LIBRES - total_dias_usados

    if request.method == 'POST':           
        try:
            cantidad_dias = int(request.form.get('cantidad_dias'))
        except (ValueError, TypeError):
            message = "Cantidad de días inválida."
            return render_template('solicitar_dias_administrativos.html', message=message, available_days=available_days)
        
        if cantidad_dias <= 0:
            message = "La cantidad de días debe ser mayor a cero."
            return render_template('solicitar_dias_administrativos.html', message=message, available_days=available_days)

        # Verificar que la nueva solicitud no exceda el máximo permitido.
        if total_dias_usados + cantidad_dias > MAX_DIAS_LIBRES:
            message = (
                f"Se excede el máximo de días administrativos permitidos (6 días por año). "
                f"Días ya usados: {total_dias_usados}, días solicitados: {cantidad_dias}."
            )
            return render_template('solicitar_dias_administrativos.html', message=message, available_days=available_days)

        # Registrar la solicitud
        fecha_solicitud = datetime.now().strftime("%Y-%m-%d")
        db.execute(
            "INSERT INTO dias_administrativos (empleado_id, cantidad_dias, fecha_solicitud, estado) VALUES (?, ?, ?, ?)",
            (empleado_id, cantidad_dias, fecha_solicitud, 'pendiente')
        )
        db.commit()
        message = "Solicitud de días administrativos registrada exitosamente."

        # Actualizar el contador tras la inserción
        total_dias_usados += cantidad_dias
        available_days = MAX_DIAS_LIBRES - total_dias_usados

    return render_template('solicitar_dias_administrativos.html', message=message, available_days=available_days)
