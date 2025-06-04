from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime, timedelta

vacaciones_bp = Blueprint('vacaciones', __name__)

@vacaciones_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_vacaciones():
    message = None
    message_type = None
    dias_solicitados = None  # para mostrar tras “Calcular”

    empleado_id = current_user.id
    db = get_db()

    # Total de días asignados al empleado
    total_vacaciones = int(current_user.dias_vacaciones)

    # Sumar sólo las vacaciones con estado 'aprobado'
    cur = db.execute(
        "SELECT SUM(cantidad_dias) AS total "
        "FROM vacaciones "
        "WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    )
    row = cur.fetchone()
    dias_usados = int(row['total']) if row['total'] is not None else 0

    # Días disponibles
    disponibles = max(0, total_vacaciones - dias_usados)

    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')

        # Validación de fechas presentes
        if not fecha_inicio or not fecha_fin:
            message = "¡No tengo una bola de cristal! Complete ambas fechas."
            message_type = "danger"
            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados
            )

        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
        except ValueError:
            message = "¿Qué está haciendo? Ponga fechas."
            message_type = "danger"
            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados
            )

        if fin < inicio:
            message = "¿Va a viajar en el tiempo?."
            message_type = "danger"
            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados
            )

        # Contar días hábiles entre inicio y fin
        dias_solicitados = contar_dias_habiles(inicio, fin, feriados_chile)

        # ¿Se presionó “Calcular” o “Enviar”?
        if request.form.get('accion') == 'calcular':
            # Sólo mostramos el resultado, no guardamos nada
            if dias_solicitados == 0:
                message = "Estos días son por cuenta de la casa... de nada."
                message_type = "danger"
            elif dias_solicitados > disponibles:
                message = f"Solicitaría {dias_solicitados} días, pero solo tiene {disponibles} días disponibles. Tírese una licencia, mejor."
                message_type = "danger"
            else:
                message = f"Vas a solicitar {dias_solicitados} días hábiles."
                message_type = "info"

            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )

        # Si llegaste aquí, asumimos que la acción es “enviar”
        # Revalidamos en el servidor
        if dias_solicitados == 0:
            message = "Estos días son por cuenta de la casa... de nada."
            message_type = "danger"
            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )

        if dias_solicitados > disponibles:
            message = f"Está solicitando {dias_solicitados} días, preo solo tiene {disponibles} días disponibles. Tírese una licencia, mejor."
            message_type = "danger"
            return render_template(
                'solicitar_vacaciones.html',
                message=message,
                message_type=message_type,
                disponibles=disponibles,
                dias_solicitados=dias_solicitados,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )

        # Registrar la solicitud con estado "pendiente"
        db.execute(
            "INSERT INTO vacaciones "
            "(empleado_id, fecha_inicio, fecha_fin, cantidad_dias, estado) "
            "VALUES (?, ?, ?, ?, ?)",
            (empleado_id, fecha_inicio, fecha_fin, dias_solicitados, 'pendiente')
        )
        db.commit()

        message = "Solicitud de vacaciones enviada. Mande fruta y vuelva con algo."
        message_type = "success"
        # Reducimos disponibles en la misma vista
        disponibles -= dias_solicitados

        # En este punto, querrás limpiar dias_solicitados o mantenerlo para mostrar
        return render_template(
            'solicitar_vacaciones.html',
            message=message,
            message_type=message_type,
            disponibles=disponibles,
            dias_solicitados=None,  # opcional: ocultar el contador tras enviar
            fecha_inicio=None,
            fecha_fin=None
        )

    # GET inicial
    return render_template(
        'solicitar_vacaciones.html',
        message=message,
        message_type=message_type,
        disponibles=disponibles,
        dias_solicitados=None,
        fecha_inicio=None,
        fecha_fin=None
    )

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
