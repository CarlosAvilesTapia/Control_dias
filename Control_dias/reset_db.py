from app import create_app
from models import get_db, init_db

app = create_app()

with app.app_context():
    db = get_db()
    # Lista de tablas a eliminar. Asegúrate de incluir todas las que tienes.
    tablas = ['vacaciones', 'horas_extras', 'dias_administrativos', 'horas_compensadas'] # Agregar después 'users', 
    for tabla in tablas:
        db.execute(f"DROP TABLE IF EXISTS {tabla};")
    db.commit()
    # Recrea las tablas ejecutando el contenido de schema.sql
    init_db()
    print("Base de datos reseteada correctamente.")
