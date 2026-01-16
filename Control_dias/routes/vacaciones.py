from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from models import get_db, create_request
from datetime import datetime, timedelta
from utils.dates import fecha_amigable

vacaciones_bp = Blueprint('vacaciones', __name__)

feriados_chile = {
    "2026-01-01",  # Año Nuevo
    "2026-04-03",  # Viernes Santo
    "2026-04-04",  # Sábado Santo
    "2026-05-01",  # Día del Trabajador
    "2026-05-21",  # Glorias Navales
    "2026-06-20",  # Día de los Pueblos Indígenas
    "2026-06-29",  # San Pedro y San Pablo
    "2026-07-16",  # Virgen del Carmen
    "2026-08-15",  # Asunción de la Virgen
    "2026-09-18",  # Independencia Nacional
    "2026-09-19",  # Glorias del Ejército
    "2026-10-12",  # Encuentro de Dos Mundos
    "2026-10-31",  # Día de las Iglesias Evangélicas
    "2026-12-08",  # Inmaculada Concepción
    "2026-12-25"   # Navidad
}

def contar_dias_habiles(inicio, fin, feriados):
    dias_habiles = 0
    actual = inicio
    while actual <= fin:
        if actual.weekday() < 5 and actual.strftime('%Y-%m-%d') not in feriados:
            dias_habiles += 1
        actual += timedelta(days=1)
    return dias_habiles


def buscar_conflicto_requests(db, user_id, new_start, new_end):
    """
    Conflicto general para VACACIONES:
    - Las vacaciones (día completo / rango) chocan con cualquier request pendiente/aprobada
      que se cruce, incluyendo administrativos de medio día.
    Requiere que la tabla requests tenga half_day_part (NULL / 'AM' / 'PM') para mostrar.
    """
    return db.execute("""
        SELECT id, request_type, start_date, end_date, status, days, half_day_part
        FROM requests
        WHERE user_id = ?
          AND status IN ('pendiente', 'aprobada')
          AND start_date <= ?
          AND end_date >= ?
        LIMIT 1
    """, (user_id, new_end, new_start)).fetchone()


@vacaciones_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_vacaciones():
    message = None
    message_type = None
    dias_solicitados = None  # para mostrar tras “Calcular”

    empleado_id = current_user.id
    db = get_db()
    current_year = datetime.now().year

    # Total de días asignados al empleado
    total_vacaciones = int(current_user.dias_vacaciones)

    # Sumar sólo las vacaciones con estado 'aprobada' del año actual
    cur = db.execute(
        """
        SELECT COALESCE(SUM(days), 0) AS total
        FROM requests
        WHERE user_id = ?
          AND request_type = 'vacaciones'
          AND status = 'aprobada'
          AND substr(start_date, 1, 4) = ?
        """,
        (empleado_id, str(current_year))
    )
    row = cur.fetchone()
    dias_usados = int(row['total']) if row and row['total'] is not None else 0

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
            message = f"Está solicitando {dias_solicitados} días, pero solo tiene {disponibles} días disponibles. Tírese una licencia, mejor."
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

        # ✅ NUEVO: validar solapamiento contra TODO (vacaciones + administrativos, incluyendo medio día)
        conflicto = buscar_conflicto_requests(db, empleado_id, fecha_inicio, fecha_fin)
        if conflicto:
            extra = ""
            if conflicto["days"] == 0.5 and conflicto.get("half_day_part"):
                extra = f" ({conflicto['half_day_part']})"

            message = (
                "Ya tienes una solicitud "
                f"({conflicto['request_type']}) {conflicto['status']} que se cruza con las fechas: "
                f"({fecha_amigable(conflicto['start_date'])} a {fecha_amigable(conflicto['end_date'])}{extra})."
            )
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

        # Registrar la solicitud SOLO en requests (tabla canónica)
        create_request(
            user_id=empleado_id,
            request_type="vacaciones",
            start_date=fecha_inicio,
            end_date=fecha_fin,
            days=dias_solicitados,
            reason=None,
            half_day_part=None  # vacaciones siempre día completo/rango
        )

        message = "Solicitud de vacaciones enviada. Mande fruta y vuelva con algo."
        message_type = "success"

        # feedback inmediato
        disponibles -= dias_solicitados

        return render_template(
            'solicitar_vacaciones.html',
            message=message,
            message_type=message_type,
            disponibles=disponibles,
            dias_solicitados=None,
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
