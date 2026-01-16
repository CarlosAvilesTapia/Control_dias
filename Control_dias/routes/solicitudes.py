from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from models import get_db
from datetime import datetime

solicitudes_bp = Blueprint("solicitudes", __name__)

@solicitudes_bp.route("/mis_solicitudes")
@login_required
def mis_solicitudes():
    db = get_db()

    # Año actual por defecto
    current_year = datetime.now().year
    selected_year = request.args.get("anio", type=int) or current_year

    # Años disponibles para el usuario (desde start_date)
    years_rows = db.execute("""
        SELECT DISTINCT CAST(substr(start_date, 1, 4) AS INTEGER) AS anio
        FROM requests
        WHERE user_id = ?
          AND start_date IS NOT NULL
        ORDER BY anio DESC
    """, (current_user.id,)).fetchall()

    available_years = [r["anio"] for r in years_rows if r["anio"] is not None] or [current_year]

    # Solicitudes filtradas por año
    solicitudes = db.execute("""
        SELECT id, request_type, created_at, status,
               start_date, end_date, days, admin_comment
        FROM requests
        WHERE user_id = ?
          AND start_date IS NOT NULL
          AND substr(start_date, 1, 4) = ?
        ORDER BY datetime(created_at) DESC
    """, (current_user.id, str(selected_year))).fetchall()

    return render_template(
        "mis_solicitudes.html",
        solicitudes=solicitudes,
        available_years=available_years,
        selected_year=selected_year
    )
