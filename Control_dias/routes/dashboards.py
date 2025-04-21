from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import get_db
from charts import create_vacation_chart, create_admin_chart, create_hours_chart

dashboards_bp = Blueprint('dashboards', __name__)

# Creación del dashboard.
@dashboards_bp.route('/dashboard')
@login_required
def dashboard():
    # Solo el administrador puede acceder al dashboard
    if current_user.role != 'administrador':
        abort(403)
    
    db = get_db()
    # Obtener el listado de empleados (por ejemplo, id, username y días asignados de vacaciones)
    employees = db.execute("SELECT id, username, dias_vacaciones FROM users").fetchall()
    return render_template('dashboard.html', employees=employees)

# Dashboard de cada empleado.
@dashboards_bp.route('/dashboard/<int:employee_id>')
@login_required
def employee_dashboard(employee_id):
    if current_user.role != 'administrador':
        abort(403)
    
    db = get_db()
    employee = db.execute("SELECT id, username, dias_vacaciones FROM users WHERE id = ?", (employee_id,)).fetchone()
    if not employee:
        abort(404)
    
    # VACACIONES:
    vac_total = employee['dias_vacaciones']
    vac_data = db.execute(
        "SELECT SUM(JULIANDAY(fecha_fin) - JULIANDAY(fecha_inicio) + 1) AS used FROM vacaciones WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    vac_used = vac_data['used'] if vac_data['used'] is not None else 0
    vac_chart = create_vacation_chart(vac_total, vac_used)
    
    # DÍAS ADMINISTRATIVOS:
    admin_max = 6  # Máximo fijo para días administrativos
    admin_data = db.execute(
        "SELECT SUM(cantidad_dias) AS used FROM dias_administrativos WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    admin_used = admin_data['used'] if admin_data['used'] is not None else 0
    admin_chart = create_admin_chart(admin_max, admin_used)
    
    # HORAS EXTRAS Y COMPENSADAS:
    extra_data = db.execute(
        "SELECT SUM(cantidad_horas) AS approved FROM horas_extras WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    extra_approved = extra_data['approved'] if extra_data['approved'] is not None else 0

    comp_data = db.execute(
        "SELECT SUM(cantidad_horas) AS compensated FROM horas_compensadas WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    comp_requested = comp_data['compensated'] if comp_data['compensated'] is not None else 0
    hours_chart = create_hours_chart(extra_approved, comp_requested)

    return render_template(
    'employee_dashboard.html',
    employee=employee,
    vac_chart=vac_chart,
    admin_chart=admin_chart,
    hours_chart=hours_chart,
    vac_total=vac_total,
    vac_used=vac_used,
    admin_max=admin_max,
    admin_used=admin_used,
    extra_approved=extra_approved,
    comp_requested=comp_requested
)


@dashboards_bp.route('/mi_dashboard')
@login_required
def mi_dashboard():
    db = get_db()
    user = current_user
    empleado_id = user.id

    # VACACIONES
    user_data = db.execute("SELECT dias_vacaciones FROM users WHERE id = ?", (empleado_id,)).fetchone()
    vac_total = user_data['dias_vacaciones']
    vac_data = db.execute(
        "SELECT SUM(JULIANDAY(fecha_fin) - JULIANDAY(fecha_inicio) + 1) AS used FROM vacaciones WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    vac_used = vac_data['used'] if vac_data['used'] is not None else 0
    vac_chart = create_vacation_chart(vac_total, vac_used)

    # DÍAS ADMINISTRATIVOS
    admin_max = 6
    admin_data = db.execute(
        "SELECT SUM(cantidad_dias) AS used FROM dias_administrativos WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    admin_used = admin_data['used'] if admin_data['used'] is not None else 0
    admin_chart = create_admin_chart(admin_max, admin_used)

    # HORAS
    result_extra = db.execute(
        "SELECT SUM(cantidad_horas) as total FROM horas_extras WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    extra_aprobadas = result_extra['total'] if result_extra['total'] is not None else 0

    result_comp = db.execute(
        "SELECT SUM(cantidad_horas) as total FROM horas_compensadas WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    compensadas = result_comp['total'] if result_comp['total'] is not None else 0

    horas_chart = create_hours_chart(extra_aprobadas, compensadas)

    return render_template(
    'mi_dashboard.html',
    user=user,
    vac_chart=vac_chart,
    admin_chart=admin_chart,
    horas_chart=horas_chart,
    vac_total=vac_total,
    vac_used=vac_used,
    admin_max=admin_max,
    admin_used=admin_used,
    extra_aprobadas=extra_aprobadas,
    compensadas=compensadas
)
