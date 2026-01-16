from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from models import get_db, create_request
from datetime import datetime, timedelta
from utils.dates import fecha_amigable

dias_administrativos_bp = Blueprint('dias_administrativos', __name__)

MAX_DIAS_ADMIN = 6.0

# Mismos feriados que vacaciones.py
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

def conflicto_requests(db, user_id, start_date, end_date, es_medio_dia, half_day_part):
    if es_medio_dia:
        return db.execute("""
            SELECT id, request_type, start_date, end_date, status, days, half_day_part
            FROM requests
            WHERE user_id = ?
              AND status IN ('pendiente','aprobada')
              AND start_date <= ?
              AND end_date >= ?
              AND (
                    days >= 1
                    OR (days = 0.5 AND half_day_part = ?)
                  )
            LIMIT 1
        """, (user_id, end_date, start_date, half_day_part)).fetchone()

    return db.execute("""
        SELECT id, request_type, start_date, end_date, status, days, half_day_part
        FROM requests
        WHERE user_id = ?
          AND status IN ('pendiente','aprobada')
          AND start_date <= ?
          AND end_date >= ?
        LIMIT 1
    """, (user_id, end_date, start_date)).fetchone()

@dias_administrativos_bp.route('/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_administrativos():
    message = None
    message_type = None
    dias_solicitados = None

    empleado_id = current_user.id
    db = get_db()
    current_year = datetime.now().year

    # Sumar administrativos aprobados del año
    cur = db.execute(
        """
        SELECT COALESCE(SUM(days), 0) AS total
        FROM requests
        WHERE user_id = ?
          AND request_type = 'administrativo'
          AND status = 'aprobada'
          AND substr(start_date, 1, 4) = ?
        """,
        (empleado_id, str(current_year))
    )
    row = cur.fetchone()
    usados = float(row['total']) if row and row['total'] is not None else 0.0
    disponibles = max(0.0, MAX_DIAS_ADMIN - usados)

    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        jornada = request.form.get('jornada', 'completo')  # completo | am | pm

        if not fecha_inicio or not fecha_fin:
            message = "¡No tengo una bola de cristal! Complete ambas fechas."
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados)

        try:
            inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
        except ValueError:
            message = "¿Qué está haciendo? Ponga fechas."
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados)

        if fin < inicio:
            message = "¿Va a viajar en el tiempo?."
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados)

        # Medio día solo permitido si es un solo día
        es_medio_dia = jornada in ('am', 'pm')
        half_day_part = None

        if es_medio_dia:
            if fecha_inicio != fecha_fin:
                message = "El medio día tiene que ser en una sola fecha. No se ponga creativo."
                message_type = "danger"
                return render_template('solicitar_administrativos.html',
                                       message=message, message_type=message_type,
                                       disponibles=disponibles, dias_solicitados=dias_solicitados,
                                       fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

            # Si el día no es hábil, 0 días (rechazo igual que vacaciones)
            if inicio.weekday() >= 5 or fecha_inicio in feriados_chile:
                dias_solicitados = 0
            else:
                dias_solicitados = 0.5

            half_day_part = 'AM' if jornada == 'am' else 'PM'
        else:
            dias_solicitados = float(contar_dias_habiles(inicio, fin, feriados_chile))
            half_day_part = None

        # Calcular vs Enviar
        if request.form.get('accion') == 'calcular':
            if dias_solicitados == 0:
                message = "Estos días son por cuenta de la casa... de nada."
                message_type = "danger"
            elif dias_solicitados > disponibles:
                message = f"Solicitaría {dias_solicitados} días, pero solo tiene {disponibles} disponibles. Otsea."
                message_type = "danger"
            else:
                message = f"Vas a solicitar {dias_solicitados} días hábiles."
                message_type = "info"

            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados,
                                   fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, jornada=jornada)

        # Enviar
        if dias_solicitados == 0:
            message = "Estos días son por cuenta de la casa... de nada."
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados,
                                   fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, jornada=jornada)

        if dias_solicitados > disponibles:
            message = f"Está solicitando {dias_solicitados} días, pero solo tiene {disponibles} disponibles. Otsea."
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados,
                                   fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, jornada=jornada)

        # Conflicto con solicitudes existentes (vacaciones y administrativos)
        conflicto = conflicto_requests(db, empleado_id, fecha_inicio, fecha_fin, es_medio_dia, half_day_part)
        if conflicto:
            extra = ""
            if conflicto['days'] == 0.5 and conflicto['half_day_part']:
                extra = f" ({conflicto['half_day_part']})"

            message = (
                "Ya tienes una solicitud "
                f"({conflicto['request_type']}) {conflicto['status']} que se cruza con: "
                f"({fecha_amigable(conflicto['start_date'])} a {fecha_amigable(conflicto['end_date'])}{extra})."
            )
            message_type = "danger"
            return render_template('solicitar_administrativos.html',
                                   message=message, message_type=message_type,
                                   disponibles=disponibles, dias_solicitados=dias_solicitados,
                                   fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, jornada=jornada)

        # Guardar en requests
        create_request(
            user_id=empleado_id,
            request_type="administrativo",
            start_date=fecha_inicio,
            end_date=fecha_fin,
            days=dias_solicitados,
            reason=None,
            half_day_part=half_day_part  # <-- necesitas extender create_request
        )

        message = "Solicitud de administrativos enviada. Vaya con dios."
        message_type = "success"
        disponibles -= dias_solicitados

        return render_template('solicitar_administrativos.html',
                               message=message, message_type=message_type,
                               disponibles=disponibles, dias_solicitados=None,
                               fecha_inicio=None, fecha_fin=None, jornada='completo')

    return render_template('solicitar_administrativos.html',
                           message=message, message_type=message_type,
                           disponibles=disponibles, dias_solicitados=None,
                           fecha_inicio=None, fecha_fin=None, jornada='completo')
