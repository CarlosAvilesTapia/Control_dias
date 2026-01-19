import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave_por_defecto')
    DATABASE = os.path.join(os.path.dirname(__file__), 'mi_base_PROD_2025.db')
    
    # Módulos de horas y compensadas apagados
    FEATURE_HORAS_EXTRAS = False
    FEATURE_COMPENSADAS = False
