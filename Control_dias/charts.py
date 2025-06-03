import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

sns.set_theme(style="whitegrid")

def _render_chart(fig):
    """Convierte una figura de matplotlib a base64 para mostrarla en HTML."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return image_base64


def create_vacation_chart(total, used):
    """
    Crea un gráfico circular (pie) para Vacaciones.
    Si total == 0 o los valores no son válidos, dibuja un texto indicativo.
    """
    # Intentamos convertir a float; si falla, lo consideramos 0
    try:
        total = float(total)
    except (TypeError, ValueError):
        total = 0.0

    try:
        used = float(used)
    except (TypeError, ValueError):
        used = 0.0

    # Si no hay vacaciones asignadas o used > total, mostramos texto
    if total <= 0 or used < 0 or used > total:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
        ax.axis('off')
        ax.text(
            0.5, 0.5,
            'No hay vacaciones\nasignadas',
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=12,
            color='gray'
        )
        return _render_chart(fig)

    # Calculamos las restantes
    restante = total - used
    # Si restante es 0 (todas usadas), también mostramos texto
    if restante <= 0:
        fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
        ax.axis('off')
        ax.text(
            0.5, 0.5,
            'Todas las vacaciones\nya están usadas',
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=12,
            color='gray'
        )
        return _render_chart(fig)
    


    # Caso normal: dibujo del pie
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.pie(
        [used, restante],
        labels=['Usadas', 'Disponibles'],
        autopct='%1.1f%%',
        startangle=90,
        colors=["#0d6efd", "#198754"],  # Bootstrap colors
        explode=(0.05, 0),
        wedgeprops={'edgecolor': 'white'}
    )
    ax.set_title("Vacaciones", fontsize=14)
    ax.axis('equal')
    return _render_chart(fig)


def create_admin_chart(maximo, usados):
    restante = max(0, maximo - usados)
    fig, ax = plt.subplots(figsize=(4, 4), dpi=100)
    ax.pie(
        [usados, restante],
        labels=['Usados', 'Disponibles'],
        autopct='%1.1f%%',
        startangle=90,
        colors=["#ffc107", "#6c757d"],  # Amarillo y gris
        explode=(0.05, 0),
        wedgeprops={'edgecolor': 'white'}
    )
    ax.set_title("Días Administrativos", fontsize=14)
    ax.axis('equal')
    return _render_chart(fig)


def create_hours_chart(aprobadas, compensadas):
    restante = max(0, aprobadas - compensadas)
    labels = ['Aprobadas', 'Compensadas', 'Disponibles']
    valores = [aprobadas, compensadas, restante]
    colores = ['#0dcaf0', '#fd7e14', '#20c997']  # Bootstrap info, orange, green

    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    bars = ax.bar(labels, valores, color=colores, edgecolor='black')
    ax.set_ylabel("Horas")
    ax.set_title("Horas Extras vs. Compensadas", fontsize=14)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5), textcoords="offset points",
                    ha='center', fontsize=10)

    return _render_chart(fig)