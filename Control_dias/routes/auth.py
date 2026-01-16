from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models import get_user_by_username, verify_password, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'administrador':
            return redirect(url_for('dashboards.dashboard'))
        else:
            return redirect(url_for('dashboards.mi_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        # Usuario inexistente
        if not user:
            error = "¿Quién es usted? ¿Es parte del equipo?"
            return render_template('login.html', error=error)

        # Usuario deshabilitado
        # (asume que ya existe la columna activo en users)
        if user['activo'] == 0:
            error = "Lo siento, usted ya no trabaja con nosotros. :("
            return render_template('login.html', error=error)

        # Password correcto
        if verify_password(user, password):
            login_user(User(
                user['id'],
                user['username'],
                user['role'],
                user['dias_vacaciones'],
                user['activo']
            ))

            if user['role'] == 'administrador':
                return redirect(url_for('dashboards.dashboard'))
            else:
                return redirect(url_for('dashboards.mi_dashboard'))

        # Password incorrecto
        error = "¿Quién es usted? ¿Es parte del equipo?"
        return render_template('login.html', error=error)

    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
