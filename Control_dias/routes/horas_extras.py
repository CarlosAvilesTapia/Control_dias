from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

horas_extras_bp = Blueprint('horas_extras', __name__)

@horas_extras_bp.route('/reportar', methods=['GET', 'POST'])
@login_required
def reportar_horas_extras():
    if not current_app.config.get("FEATURE_HORAS_EXTRAS", False):
        return render_template(
            "feature_disabled.html",
            message="Ya no hay horas extras. Póngase la camiseta!"
        ), 403
        
    message = None
    message_type = None
    empleado_id = current_user.id

    if request.method == 'POST':
        fecha = request.form.get('fecha')  # esperado: YYYY-MM-DD

        try:
            cantidad_horas = float(request.form.get('cantidad_horas'))
        except (ValueError, TypeError):
            message = "¿Qué está haciendo? Ingrese la cantidad de horas."
            message_type = "danger"
            return render_template(
                'reportar_horas_extras.html',
                message=message,
                message_type=message_type
            )

        motivo = request.form.get('motivo')

        if not fecha or cantidad_horas <= 0 or not motivo:
            message = "Por favor, haga el reporte como se debe y complete todo."
            message_type = "danger"
            return render_template(
                'reportar_horas_extras.html',
                message=message,
                message_type=message_type
            )

        # Verificación si las horas son dobles.
        if request.form.get('doblar'):
            cantidad_horas *= 2

        # Calcular año desde la fecha ingresada (YYYY-MM-DD)
        try:
            anio = int(fecha[:4])
        except (ValueError, TypeError):
            message = "La fecha no tiene un formato válido (YYYY-MM-DD)."
            message_type = "danger"
            return render_template(
                'reportar_horas_extras.html',
                message=message,
                message_type=message_type
            )

        db = get_db()
        db.execute(
            """
            INSERT INTO horas_extras (empleado_id, fecha, cantidad_horas, motivo, estado, anio)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (empleado_id, fecha, cantidad_horas, motivo, 'pendiente', anio)
        )
        db.commit()

        message = "Horas extras reportadas exitosamente ¡Muchas gracias por su esfuerzo!"
        message_type = "success"

    return render_template(
        'reportar_horas_extras.html',
        message=message,
        message_type=message_type
    )


# Nueva ruta para solicitar horas compensadas (convertir horas extras en tiempo libre)
@horas_extras_bp.route('/solicitar_compensadas', methods=['GET', 'POST'])
@login_required
def solicitar_horas_compensadas():
    if not current_app.config.get("FEATURE_COMPENSADAS", False):
        return render_template(
            "feature_disabled.html",
            message="Si no hay horas extras... ¿De dónde va a sacar compensadas?"
        ), 403

    message = None
    message_type = None
    empleado_id = current_user.id
    db = get_db()
    current_year = datetime.now().year

    # Total de horas extras aprobadas (solo del año actual)
    result_extra = db.execute(
        """
        SELECT COALESCE(SUM(cantidad_horas), 0) AS total
        FROM horas_extras
        WHERE empleado_id = ?
          AND estado = 'aprobado'
          AND anio = ?
        """,
        (empleado_id, current_year)
    ).fetchone()
    total_extras_aprobadas = float(result_extra['total'])

    # Total de horas compensadas ya aprobadas (solo del año actual)
    result_compensadas = db.execute(
        """
        SELECT COALESCE(SUM(cantidad_horas), 0) AS total
        FROM horas_compensadas
        WHERE empleado_id = ?
          AND estado = 'aprobado'
          AND anio = ?
        """,
        (empleado_id, current_year)
    ).fetchone()
    total_compensadas = float(result_compensadas['total'])

    # Horas disponibles = aprobadas - compensadas (del año actual)
    available_hours = total_extras_aprobadas - total_compensadas

    if request.method == 'POST':
        try:
            requested_hours = float(request.form.get('cantidad_horas'))
        except (ValueError, TypeError):
            message = "¿Qué está haciendo? Ingrese la cantidad de horas que quiere solicitar."
            message_type = "danger"
            return render_template(
                'solicitar_horas_compensadas.html',
                message=message,
                message_type=message_type,
                available_hours=available_hours
            )

        if requested_hours <= 0:
            message = "Pida una hora por lo menos ¿Para qué se metió acá?"
            message_type = "danger"
            return render_template(
                'solicitar_horas_compensadas.html',
                message=message,
                message_type=message_type,
                available_hours=available_hours
            )

        if requested_hours > available_hours:
            message = f"Parece que no se ha puesto la camiseta. Solo tiene disponibles: {available_hours} horas."
            message_type = "danger"
            return render_template(
                'solicitar_horas_compensadas.html',
                message=message,
                message_type=message_type,
                available_hours=available_hours
            )

        # Registrar la solicitud de horas compensadas con estado "pendiente"
        fecha_solicitud = datetime.now().strftime("%Y-%m-%d")
        anio = int(fecha_solicitud[:4])  # o current_year

        db.execute(
            """
            INSERT INTO horas_compensadas (empleado_id, cantidad_horas, fecha_solicitud, estado, anio)
            VALUES (?, ?, ?, ?, ?)
            """,
            (empleado_id, requested_hours, fecha_solicitud, 'pendiente', anio)
        )
        db.commit()

        message = "Solicitud de horas compensadas enviada. Vaya con dios."
        message_type = "success"

    return render_template(
        'solicitar_horas_compensadas.html',
        message=message,
        message_type=message_type,
        available_hours=available_hours
    )
