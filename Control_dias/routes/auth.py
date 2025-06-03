from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user, UserMixin
from models import get_user_by_username, verify_password

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

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

        if user and verify_password(user, password):
            login_user(User(user['id'], user['username'], user['role']))
            if user['role'] == 'administrador':
                return redirect(url_for('dashboards.dashboard'))
            else:
                return redirect(url_for('dashboards.mi_dashboard'))
        else:
            error = "¿Quién es usted? ¿Es parte del equipo?"
            return render_template('login.html', error=error)

    return render_template('login.html')           

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
