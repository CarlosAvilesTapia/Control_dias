from flask import current_app, abort, render_template

def feature_required(flag_name: str, template="feature_disabled.html", status_code=403, message=None):
    if not current_app.config.get(flag_name, False):
        return render_template(
            template,
            title="Función temporalmente deshabilitada",
            message=message or "Por disposición de la autoridad, esta función está pausada por ahora."
        ), status_code
    return None
