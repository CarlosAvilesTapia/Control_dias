from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import get_db
from charts import create_vacation_chart, create_admin_chart, create_hours_chart
from routes.vacaciones import contar_dias_habiles, feriados_chile
from datetime import datetime

dashboards_bp = Blueprint('dashboards', __name__)

# Dashboard general (solo admin)
@dashboards_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'administrador':
        abort(403)

    db = get_db()
    employees = db.execute(
        "SELECT id, username, dias_vacaciones FROM users"
    ).fetchall()

    return render_template('dashboard.html', employees=employees)


# Dashboard de cada empleado (admin)
@dashboards_bp.route('/dashboard/<int:employee_id>')
@login_required
def employee_dashboard(employee_id):
    if current_user.role != 'administrador':
        abort(403)

    db = get_db()
    employee = db.execute(
        "SELECT id, username, dias_vacaciones FROM users WHERE id = ?",
        (employee_id,)
    ).fetchone()
    if not employee:
        abort(404)

    # VACACIONES
    vac_total = employee['dias_vacaciones']
    # Traemos cada rango aprobado en lugar de hacer SUM en SQL
    vac_rows = db.execute("""
        SELECT fecha_inicio, fecha_fin
        FROM vacaciones
        WHERE empleado_id = ? AND estado = 'aprobado'
    """, (employee_id,)).fetchall()

    vac_used = 0
    for r in vac_rows:
        inicio = datetime.strptime(r['fecha_inicio'], "%Y-%m-%d")
        fin    = datetime.strptime(r['fecha_fin'],    "%Y-%m-%d")
        vac_used += contar_dias_habiles(inicio, fin, feriados_chile)

    vac_available = max(0, vac_total - vac_used)
    vac_chart     = create_vacation_chart(vac_total, vac_used)

    # DÍAS ADMINISTRATIVOS
    admin_max = 6.0
    admin_used_row = db.execute(
        "SELECT SUM(cantidad_dias) AS used "
        "FROM dias_administrativos WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    admin_used = float(admin_used_row['used']) if admin_used_row['used'] is not None else 0.0
    admin_available = max(0, admin_max - admin_used)
    admin_chart = create_admin_chart(admin_max, admin_used)

    # HORAS EXTRAS
    extra_row = db.execute(
        "SELECT SUM(cantidad_horas) AS approved "
        "FROM horas_extras WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    extra_approved = float(extra_row['approved']) if extra_row['approved'] is not None else 0.0

    # HORAS COMPENSADAS
    comp_row = db.execute(
        "SELECT SUM(cantidad_horas) AS compensated "
        "FROM horas_compensadas WHERE empleado_id = ? AND estado = 'aprobado'",
        (employee_id,)
    ).fetchone()
    comp_requested = float(comp_row['compensated']) if comp_row['compensated'] is not None else 0.0

    hours_available = max(0.0, extra_approved - comp_requested)
    hours_chart = create_hours_chart(extra_approved, comp_requested)

    return render_template(
        'employee_dashboard.html',
        employee=employee,
        vac_total=vac_total,
        vac_used=vac_used,
        vac_available=vac_available,
        vac_chart=vac_chart,
        admin_max=admin_max,
        admin_used=admin_used,
        admin_available=admin_available,
        admin_chart=admin_chart,
        extra_approved=extra_approved,
        comp_requested=comp_requested,
        hours_available=hours_available,
        hours_chart=hours_chart
    )


# Dashboard personal (empleado)
@dashboards_bp.route('/mi_dashboard')
@login_required
def mi_dashboard():
    db = get_db()
    empleado_id = current_user.id

    # VACACIONES
    vac_total = current_user.dias_vacaciones
    vac_rows  = db.execute("""
        SELECT fecha_inicio, fecha_fin
        FROM vacaciones
        WHERE empleado_id = ? AND estado = 'aprobado'
    """, (empleado_id,)).fetchall()

    vac_used = sum(
        contar_dias_habiles(
            datetime.strptime(r['fecha_inicio'], "%Y-%m-%d"),
            datetime.strptime(r['fecha_fin'],    "%Y-%m-%d"),
            feriados_chile
        )
        for r in vac_rows
    )

    vac_available = max(0, vac_total - vac_used)
    vac_chart     = create_vacation_chart(vac_total, vac_used)

    # DÍAS ADMINISTRATIVOS
    admin_max = 6.0
    admin_used_row = db.execute(
        "SELECT SUM(cantidad_dias) AS used "
        "FROM dias_administrativos WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    admin_used = float(admin_used_row['used']) if admin_used_row['used'] is not None else 0.0
    admin_available = max(0, admin_max - admin_used)
    admin_chart = create_admin_chart(admin_max, admin_used)

    # HORAS EXTRAS y COMPENSADAS
    extra_row = db.execute(
        "SELECT SUM(cantidad_horas) AS approved "
        "FROM horas_extras WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    extra_approved = float(extra_row['approved']) if extra_row['approved'] is not None else 0.0

    comp_row = db.execute(
        "SELECT SUM(cantidad_horas) AS compensated "
        "FROM horas_compensadas WHERE empleado_id = ? AND estado = 'aprobado'",
        (empleado_id,)
    ).fetchone()
    comp_requested = float(comp_row['compensated']) if comp_row['compensated'] is not None else 0.0

    hours_available = max(0.0, extra_approved - comp_requested)
    hours_chart = create_hours_chart(extra_approved, comp_requested)

    return render_template(
        'mi_dashboard.html',
        user=current_user,
        vac_total=vac_total,
        vac_used=vac_used,
        vac_available=vac_available,
        vac_chart=vac_chart,
        admin_max=admin_max,
        admin_used=admin_used,
        admin_available=admin_available,
        admin_chart=admin_chart,
        extra_approved=extra_approved,
        comp_requested=comp_requested,
        hours_available=hours_available,
        horas_chart=hours_chart
    )
