from datetime import datetime

def fecha_amigable(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
        except ValueError:
            return value
