import matplotlib.pyplot as plt
import uuid
import os
from django.conf import settings

def generate_chart(chart_data):
    x = chart_data["x"]
    y = chart_data["y"]

    plt.figure(figsize=(5, 3))
    plt.plot(x, y, marker="o", linestyle="-", color="b")
    plt.xlabel("Eixo X")
    plt.ylabel("Eixo Y")
    plt.title("Gráfico Gerado pela IA")

    # Gerar um nome único para o arquivo
    filename = f"chart_{uuid.uuid4().hex}.png"
    filepath = os.path.join(settings.MEDIA_ROOT, "charts", filename)

    # Criar a pasta 'charts' dentro de 'media', se não existir
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Salvar a imagem
    plt.savefig(filepath)
    plt.close()

    # Retornar a URL acessível no servidor local
    return f"http://127.0.0.1:8000/media/charts/{filename}"
