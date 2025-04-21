from app import create_app
from models import create_user

app = create_app()

with app.app_context():
    # Crear un usuario administrador
    create_user('admin', 'tu_contraseña_segura', role='administrador', dias_vacaciones=20)
    # Crear un usuario empleado
    create_user('empleado1', 'otra_contraseña_segura', role='empleado', dias_vacaciones=15)
    print("Usuarios creados exitosamente.")
