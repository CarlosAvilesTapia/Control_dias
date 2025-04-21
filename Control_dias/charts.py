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
    restante = max(0, total - used)
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