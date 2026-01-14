from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime, timedelta

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

    # Sumar sólo las vacaciones con estado 'aprobado' del año actual
    cur = db.execute(
        """
        SELECT COALESCE(SUM(cantidad_dias), 0) AS total
        FROM vacaciones
        WHERE empleado_id = ?
          AND estado = 'aprobado'
          AND anio = ?
        """,
        (empleado_id, current_year)
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

        # Año de la solicitud: por simplicidad tomamos el año de fecha_inicio
        # (si algún día permites rangos que crucen año, conviene decidir regla)
        anio = int(fecha_inicio[:4])

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
            """
            INSERT INTO vacaciones (empleado_id, fecha_inicio, fecha_fin, cantidad_dias, estado, anio)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (empleado_id, fecha_inicio, fecha_fin, dias_solicitados, 'pendiente', anio)
        )
        db.commit()

        message = "Solicitud de vacaciones enviada. Mande fruta y vuelva con algo."
        message_type = "success"
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
