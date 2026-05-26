
import openai
from google.cloud import texttospeech
from django.conf import settings
import os
import re
import logging

# Configuração de logs
logging.basicConfig(level=logging.INFO)

def analyze_response(question_text, response_text, question_id):
    openai.api_key = os.getenv('OPENAI_API_KEY')
 

    # Chamada à API do OpenAI
    content = f"""
    Fornecer feedback em português sobre a seguinte resposta: {response_text}, considerando que a pergunta foi: {question_text}.
    Use a segunda pessoa ao se dirigir ao usuário.
    Sempre forneça um 'Exemplo de resposta ideal:' (mesmo que a resposta seja adequada).
    Sempre forneça uma 'Classificação:' (um número inteiro entre 0 e 20, obrigatório).

    Exemplo de formato esperado:
    Feedback: [feedback construtivo aqui]
    Exemplo de resposta ideal: [exemplo de resposta ideal aqui]
    Classificação: [número entre 0 e 20]
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "Você é um assistente especialista em analisar respostas de entrevistas e fornecer feedback construtivo."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        max_tokens=500,  # Aumente o limite
        temperature=0.5
    )

    content = response['choices'][0]['message']['content']
    logging.info(f"Resposta completa do OpenAI: {content}")

    # Extrair feedback, resposta ideal e classificação usando regex
    feedback_match = re.search(r"Feedback:(.*?)Exemplo de resposta ideal:", content, re.DOTALL)
    ideal_match = re.search(r"Exemplo de resposta ideal:(.*?)Classificação:", content, re.DOTALL)
    rating_match = re.search(r"Classificação:\s*(\d+)", content)

    feedback = feedback_match.group(1).strip() if feedback_match else "N/A"
    resposta_ideal = ideal_match.group(1).strip() if ideal_match else "N/A"
    if not resposta_ideal or resposta_ideal == "N/A":
        resposta_ideal = "A resposta fornecida já é ideal. Parabéns!"

    classificacao = 0
    if rating_match:
        try:
            classificacao = int(rating_match.group(1))
            if not 0 <= classificacao <= 20:
                logging.warning(f"Classificação fora do intervalo: {classificacao}. Definindo como 0.")
                classificacao = 0
        except ValueError:
            logging.error("Falha ao converter a classificação para inteiro. Definindo como 0.")
    else:
        logging.error("A resposta do OpenAI não incluiu uma classificação. Verifique a solicitação e o formato da resposta.")
        # Estimativa simples com base no feedback
        if "ótimo" in feedback.lower() or "excelente" in feedback.lower():
            classificacao = 20
        elif "bom" in feedback.lower():
            classificacao = 15
        else:
            classificacao = 5

    # Gerar áudios
    client = texttospeech.TextToSpeechClient()
    audio_abs_dir = os.path.join(settings.MEDIA_ROOT, "feedback_audio")
    os.makedirs(audio_abs_dir, exist_ok=True)

    feedback_audio_path = os.path.join(audio_abs_dir, "feedback.mp3")
    ideal_audio_path = os.path.join(audio_abs_dir, f"ideal_response_{question_id}.mp3")

    def generate_audio(text, path):
        if text and text != "N/A":
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="pt-BR", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            response_audio = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            with open(path, "wb") as audio_file:
                audio_file.write(response_audio.audio_content)

    generate_audio(feedback, feedback_audio_path)
    generate_audio(resposta_ideal, ideal_audio_path)

    return {
        "feedback_text": feedback,
        "feedback_audio": f"feedback_audio/feedback.mp3",
        "ideal_text": resposta_ideal,
        "ideal_audio": f"feedback_audio/ideal_response_{question_id}.mp3",
        "rating": classificacao
    }