from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime, timedelta

vacaciones_bp = Blueprint('vacaciones', __name__)

@vacaciones_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_vacaciones():
    message = None
    empleado_id = current_user.id
    db = get_db()

    # Total de días asignados al empleado (ingresado al momento de registro)
    total_vacaciones = int(current_user.dias_vacaciones)

    # Consultar la cantidad de días ya utilizados (por solicitudes aprobadas)
    cur = db.execute(
        "SELECT SUM(JULIANDAY(fecha_fin) - JULIANDAY(fecha_inicio) + 1) AS total FROM vacaciones WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    )
    row = cur.fetchone()
    dias_usados = int(row['total']) if row['total'] is not None else 0

    # Días disponibles (no negativos)
    disponibles = max(0, total_vacaciones - dias_usados)

    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        if not fecha_inicio or not fecha_fin:
            message = "No tenemos bola de cristal. Complete las fechas."
            return render_template('solicitar_vacaciones.html', message=message, disponibles=disponibles)
        
        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
            if fin < inicio:
                message = "¿Va a viajar en el tiempo? La fecha final debe ser posterior a la fecha inicio."
                return render_template('solicitar_vacaciones.html', message=message, disponibles=disponibles)
            
            dias_solicitados = contar_dias_habiles(inicio, fin, feriados_chile)

        except ValueError:
            message = "No entiendo su idea."
            return render_template('solicitar_vacaciones.html', message=message, disponibles=disponibles)
        
        if dias_solicitados > disponibles:
            dia_palabra = "día" if disponibles == 1 else "días"
            message = f"¡Ubíquese! Ha solicitado {dias_solicitados} días, pero solo tiene {disponibles} {dia_palabra} disponibles."
            return render_template('solicitar_vacaciones.html', message=message, disponibles=disponibles)
        
        # Registrar la solicitud con estado "pendiente"
        db.execute(
            "INSERT INTO vacaciones (empleado_id, fecha_inicio, fecha_fin, estado) VALUES (?, ?, ?, ?)",
            (empleado_id, fecha_inicio, fecha_fin, 'pendiente')
        )
        db.commit()
        message = "Solicitud de vacaciones enviada. Mande fruta y vuelva con algo."
        disponibles = max(0, disponibles - dias_solicitados)

    return render_template('solicitar_vacaciones.html', message=message, disponibles=disponibles)

feriados_chile = {
                "2025-01-01",  # Año Nuevo
                "2025-04-18",  # Viernes Santo
                "2025-04-19",  # Sábado Santo
                "2025-05-01",  # Día del Trabajador
                "2025-05-21",  # Día de las Glorias Navales
                "2025-06-20",  # Nuevo: Día de los Pueblos Indígenas (ajustado según tu indicación)
                "2025-06-29",  # San Pedro y San Pablo
                "2025-07-16",  # Virgen del Carmen
                "2025-08-15",  # Asunción de la Virgen
                "2025-09-18",  # Independencia Nacional
                "2025-09-19",  # Día de las Glorias del Ejército
                "2025-10-31",  # Nuevo: Día de las Iglesias Evangélicas
                "2025-12-08",  # Inmaculada Concepción
                "2025-12-25"   # Navidad
            }

def contar_dias_habiles(inicio, fin, feriados):
    dias_habiles = 0
    actual = inicio
    while actual <= fin:
        if actual.weekday() < 5 and actual.strftime('%Y-%m-%d') not in feriados:
            dias_habiles += 1
        actual += timedelta(days=1)
    return dias_habiles
