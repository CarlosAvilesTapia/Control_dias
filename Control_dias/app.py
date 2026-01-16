from flask import Flask, redirect, url_for
from config import Config
from models import close_db, init_db, get_db, User
from flask_login import LoginManager, UserMixin
from utils.dates import fecha_amigable


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Inicializa la base de datos
    with app.app_context():
        init_db()

    # Cierra la conexión a la base de datos al terminar la aplicación
    app.teardown_appcontext(close_db)

    # Configuración login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # Función de callback para cargar el usuario (se ejecuta automáticamente)
    @login_manager.user_loader
    def load_user(user_id):
        db = get_db()
        user_record = db.execute(
            "SELECT * FROM users WHERE id = ? AND activo = 1",
            (user_id,)
        ).fetchone()

        if user_record is None:
            return None

        return User(
            user_record['id'],
            user_record['username'],
            user_record['role'],
            user_record['dias_vacaciones'],
            user_record['activo']
        )

    # Importa y registra los Blueprints de rutas
    from routes.auth import auth_bp
    from routes.vacaciones import vacaciones_bp
    from routes.horas_extras import horas_extras_bp
    from routes.dias_administrativos import dias_administrativos_bp
    from routes.admin import admin_bp
    from routes.dashboards import dashboards_bp
    from routes.solicitudes import solicitudes_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(vacaciones_bp, url_prefix='/vacaciones')
    app.register_blueprint(horas_extras_bp, url_prefix='/horas_extras')
    app.register_blueprint(dias_administrativos_bp, url_prefix='/dias_administrativos')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(dashboards_bp)
    app.register_blueprint(solicitudes_bp)

    app.jinja_env.filters['fecha'] = fecha_amigable


    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
