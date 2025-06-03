# create_users.py

from app import create_app
from models import create_user

app = create_app()

with app.app_context():
    # 1) Administrador
    create_user(
        username="jcerda",
        password="jdcr1260",
        role="administrador",
        dias_vacaciones=20
    )

    # 2) Empleado: caviles
    create_user(
        username="caviles",
        password="cfat1537",
        role="empleado",
        dias_vacaciones=30
    )

    # 3) Empleado: fgarcia
    create_user(
        username="fgarcia",
        password="fhgv9925",
        role="empleado",
        dias_vacaciones=15
    )

    # 4) Empleado: ljaque
    create_user(
        username="ljaque",
        password="lajl7319",
        role="empleado",
        dias_vacaciones=15
    )

    # 5) Empleado: colivares
    create_user(
        username="colivares",
        password="cfh1215",
        role="empleado",
        dias_vacaciones=15
    )

    # 6) Empleado: hgalvez
    create_user(
        username="hgalvez",
        password="hfge6360",
        role="empleado",
        dias_vacaciones=20
    )

    # 7) Empleado: pencina
    create_user(
        username="pencina",
        password="paer1392",
        role="empleado",
        dias_vacaciones=0
    )

    print("Usuarios creados exitosamente.")
