import os
import logging
import tempfile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Interview, Question, Answer, Position
from curriculum.models import User
from .serializers import InterviewSerializer, QuestionSerializer
from .utils import analyze_response
from django.conf import settings
from google.cloud import texttospeech
import openai
from uuid import UUID
from pydub import AudioSegment

import PyPDF2
from docx import Document

# Configuração de logs
logging.basicConfig(level=logging.INFO)


class InterviewAPIView(APIView):
    def post(self, request):
        user_id = request.data.get("user_id")
        position_id = request.data.get("position_id")
        job_description = request.data.get("job_description")
        cargo = request.data.get("cargo")
        empresa = request.data.get("empresa")
        language = request.data.get("idiomaEntrevista")

        try:
            user = User.objects.get(id=user_id)  # Usa o modelo User correto
            position = Position.objects.get(id=position_id)
            interview = Interview.objects.create(user=user, position=position, empresa=empresa)
            

            # Configurações do OpenAI
            openai.api_key = os.getenv('OPENAI_API_KEY')


            prompts = [
                "Generate an interview question focused on the candidate's technical skills...",
                "Generate an interview question about the candidate's experience with teamwork...",
                "Generate a clear and concise interview question that explores the candidate's salary expectations for the position.",
                "Generate an interview question that asks about problem-solving abilities...",
                "Generate an interview question focused on leadership and project management skills...",
                
            ]

            questions = []
            for prompt in prompts:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {
                            "role": "user",
                            # "content": f"{prompt} Job description:\n{job_description}\nResume:\n{user.resume}\nLanguage:\n{language}",
                            "content": f"{prompt} Job description:\n{job_description}\nPosition:\n{cargo}\nLanguage:\n{language}\nEmpresa:\n{empresa}",
                        },
                    ],
                    max_tokens=150,
                    temperature=0.7,
                )
                question_text = response["choices"][0]["message"]["content"].strip()
                questions.append(question_text)

            # Gera áudio e salva no banco
            audio_dir = os.path.join(settings.MEDIA_ROOT, "audios")
            os.makedirs(audio_dir, exist_ok=True)

            serialized_questions = []
            for i, text in enumerate(questions):
                question = Question.objects.create(interview=interview, text=text)
                audio_filename = f"question_{question.id}.mp3"
                audio_path = os.path.join(audio_dir, audio_filename)
                audio_rel_path = f"audios/{audio_filename}"

                # Geração do áudio usando Google Cloud Text-to-Speech
                client = texttospeech.TextToSpeechClient()
                synthesis_input = texttospeech.SynthesisInput(text=text)
                voice = texttospeech.VoiceSelectionParams(
                    language_code=language, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                )
                audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
                response_audio = client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )

                with open(audio_path, "wb") as audio_file:
                    audio_file.write(response_audio.audio_content)

                question.audio_path = audio_rel_path
                question.save()
                serialized_questions.append(question)

            interview_serializer = InterviewSerializer(interview)
            questions_serializer = QuestionSerializer(serialized_questions, many=True)

            return Response(
                {"interview": interview_serializer.data, "questions": questions_serializer.data},
                status=status.HTTP_201_CREATED,
            )

        except User.DoesNotExist:
            return Response({"error": "Usuário não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Position.DoesNotExist:
            return Response({"error": "Posição não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AnswerQuestionAPIView(APIView):
    def put(self, request, interview_id, question_id):
        try:
            question = Question.objects.get(id=question_id)
            interview = Interview.objects.get(id=interview_id)
            response_text = None

            if "response" in request.data:
                response_text = request.data["response"]
            elif "audio_file" in request.FILES:
                audio_file = request.FILES["audio_file"]
                logging.info(f"Arquivo de áudio recebido: {audio_file.name}, tamanho: {audio_file.size}, tipo: {audio_file.content_type}")

                # Validar o arquivo
                if audio_file.size < 1000:  # Mínimo 1KB
                    logging.error("Arquivo de áudio muito pequeno.")
                    return Response({"error": "O arquivo de áudio é muito pequeno. Grave novamente."}, status=status.HTTP_400_BAD_REQUEST)

                allowed_mime_types = ["audio/m4a", "audio/mp4", "audio/webm", "audio/mpeg", "audio/wav"]
                if audio_file.content_type not in allowed_mime_types:
                    logging.error(f"Tipo MIME não suportado: {audio_file.content_type}")
                    return Response({"error": f"Formato de áudio não suportado: {audio_file.content_type}. Use m4a, mp4, webm, mp3 ou wav."}, status=status.HTTP_400_BAD_REQUEST)

                # Converter para mp3
                with tempfile.NamedTemporaryFile(suffix=f".{audio_file.name.split('.')[-1]}", delete=False) as temp_input:
                    for chunk in audio_file.chunks():
                        temp_input.write(chunk)
                    temp_input_path = temp_input.name

                temp_output_path = temp_input_path.replace(temp_input_path.split('.')[-1], "mp3")
                try:
                    audio = AudioSegment.from_file(temp_input_path)
                    audio.export(temp_output_path, format="mp3")
                    logging.info(f"Arquivo convertido para mp3: {temp_output_path}")
                except Exception as e:
                    logging.error(f"Erro ao converter áudio para mp3: {str(e)}")
                    os.remove(temp_input_path)
                    return Response({"error": "Falha ao converter o áudio para um formato compatível."}, status=status.HTTP_400_BAD_REQUEST)

                openai.api_key = os.getenv('OPENAI_API_KEY')

                try:
                    # Usar idioma da entrevista
                    language = interview.idiomaEntrevista if hasattr(interview, 'idiomaEntrevista') else "pt"
                    with open(temp_output_path, "rb") as mp3_file:
                        transcription = openai.Audio.transcribe(
                            model="whisper-1",
                            file=mp3_file,
                            language=language
                        )
                    response_text = transcription["text"]
                    logging.info(f"Transcrição bem-sucedida: {response_text}")
                except openai.error.InvalidRequestError as e:
                    logging.error(f"Erro na API Whisper: {str(e)}")
                    return Response({"error": f"Erro ao transcrever o áudio: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    logging.error(f"Erro inesperado na transcrição: {str(e)}")
                    return Response({"error": f"Falha ao processar o áudio: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
                finally:
                    # Limpar arquivos temporários
                    if os.path.exists(temp_input_path):
                        os.remove(temp_input_path)
                    if os.path.exists(temp_output_path):
                        os.remove(temp_output_path)

            if response_text:
                try:
                    response_analysis = analyze_response(question.text, response_text, question_id)
                    feedback = response_analysis["feedback_text"]
                    resposta_ideal = response_analysis["ideal_text"]
                    classificacao = response_analysis["rating"]

                    # Salvar a resposta no banco
                    answer = Answer.objects.create(
                        question=question,
                        response=response_text,
                        feedback=feedback
                    )

                    media_url = settings.MEDIA_URL
                    return Response(
                        {
                            "feedback": feedback,
                            "transcription": response_text,
                            "ideal": resposta_ideal,
                            "rating": classificacao,
                            "feedback_audio": f"{media_url}{response_analysis.get('feedback_audio')}",
                            "ideal_audio": f"{media_url}{response_analysis.get('ideal_audio')}"
                        },
                        status=status.HTTP_200_OK,
                    )
                except ValueError as e:
                    logging.error(f"Erro ao processar a análise da resposta: {str(e)}")
                    return Response({"error": f"Erro ao processar a resposta: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Nenhuma resposta fornecida."}, status=status.HTTP_400_BAD_REQUEST)

        except Question.DoesNotExist:
            logging.error(f"Pergunta não encontrada: ID {question_id}")
            return Response({"error": "Pergunta não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Interview.DoesNotExist:
            logging.error(f"Entrevista não encontrada: ID {interview_id}")
            return Response({"error": "Entrevista não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
            return Response({"error": f"Erro interno do servidor: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class InterviewListView(APIView):
    def post(self, request):
        # Obter o user_id do corpo da requisição (JSON)
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "O campo 'user_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Validar se o user_id é um UUID válido
            user_id = UUID(user_id)

            # Filtrar as entrevistas pelo user_id
            interviews = Interview.objects.filter(user_id=user_id)

            # Serializar os dados das entrevistas
            serializer = InterviewSerializer(interviews, many=True)

            # Retornar sempre um array, mesmo que vazio
            return Response(serializer.data, status=status.HTTP_200_OK)

        except ValueError:
            return Response(
                {"error": "O campo 'user_id' deve ser um UUID válido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class UpdateInterviewRating(APIView):
    def put(self, request, interview_id):
        try:
            # Obter a entrevista pelo ID
            interview = Interview.objects.get(id=interview_id)
            
            # Atualizar a classificação total
            classificacao_total = request.data.get("classificacao_total")
            if classificacao_total is not None:
                interview.classificacao = classificacao_total
                interview.save()
            
            return Response({"message": "Classificação atualizada com sucesso!"}, status=status.HTTP_200_OK)
        except Interview.DoesNotExist:
            return Response({"error": "Entrevista não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteInterviewView(APIView):
    def delete(self, request, interview_id):
        try:
            # Converter o ID para inteiro (garantindo que seja numérico)
            interview_id = int(interview_id)

            # Buscar a entrevista pelo ID
            interview = Interview.objects.get(id=interview_id)

            # Excluir a entrevista
            interview.delete()

            return Response(
                {"message": "Entrevista excluída com sucesso."},
                status=status.HTTP_200_OK
            )
        except ValueError:
            return Response(
                {"error": "O campo 'interview_id' deve ser um número inteiro válido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Interview.DoesNotExist:
            return Response(
                {"error": "Entrevista não encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserInterviewCountView(APIView):
    def post(self, request):
        # Obter o user_id do corpo da requisição (JSON)
        user_id = request.data.get("user_id")

        if not user_id:
            return Response(
                {"error": "O campo 'user_id' é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Validar se o user_id é um UUID válido
            user_id = UUID(user_id)

            # Contar as entrevistas do usuário
            interview_count = Interview.objects.filter(user_id=user_id).count()

            # Retornar a contagem
            return Response(
                {"interview_count": interview_count},
                status=status.HTTP_200_OK
            )

        except ValueError:
            return Response(
                {"error": "O campo 'user_id' deve ser um UUID válido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        



class CVAnalysisAPIView(APIView):
    def post(self, request):
        try:
            # Validate file presence
            if 'cv_file' not in request.FILES:
                logging.error("Nenhum arquivo de CV enviado.")
                return Response({"error": "Nenhum arquivo de CV enviado."}, status=status.HTTP_400_BAD_REQUEST)

            cv_file = request.FILES['cv_file']
            logging.info(f"Arquivo de CV recebido: {cv_file.name}, tamanho: {cv_file.size}, tipo: {cv_file.content_type}")

            # Validate file size (1MB = 1,048,576 bytes)
            if cv_file.size > 1 * 1024 * 1024:
                logging.error(f"Arquivo excede 1MB: {cv_file.size} bytes")
                return Response({"error": "O arquivo excede o tamanho máximo de 1MB."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate file format
            allowed_extensions = ['.pdf', '.docx']
            file_extension = os.path.splitext(cv_file.name)[1].lower()
            if file_extension not in allowed_extensions:
                logging.error(f"Formato de arquivo não suportado: {file_extension}")
                return Response({"error": f"Formato de arquivo não suportado: {file_extension}. Use .pdf ou .docx."}, status=status.HTTP_400_BAD_REQUEST)

            # Extract text from file
            text = ""
            if file_extension == '.pdf':
                try:
                    pdf_reader = PyPDF2.PdfReader(cv_file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    logging.info(f"Texto extraído do PDF: {len(text)} caracteres")
                except Exception as e:
                    logging.error(f"Erro ao extrair texto do PDF: {str(e)}")
                    return Response({"error": "Falha ao processar o arquivo PDF."}, status=status.HTTP_400_BAD_REQUEST)
            elif file_extension == '.docx':
                try:
                    doc = Document(cv_file)
                    for para in doc.paragraphs:
                        text += para.text + "\n"
                    logging.info(f"Texto extraído do DOCX: {len(text)} caracteres")
                except Exception as e:
                    logging.error(f"Erro ao extrair texto do DOCX: {str(e)}")
                    return Response({"error": "Falha ao processar o arquivo DOCX."}, status=status.HTTP_400_BAD_REQUEST)

            if not text.strip():
                logging.error("Nenhum texto extraído do arquivo.")
                return Response({"error": "O arquivo está vazio ou não contém texto legível."}, status=status.HTTP_400_BAD_REQUEST)

            # Analyze CV with GPT-4
            openai.api_key = os.getenv('OPENAI_API_KEY')
            prompt = f"""
            Analise o seguinte texto de um CV em português e forneça uma avaliação detalhada. Liste 3-5 pontos fortes e 3-5 pontos fracos em formato de bullet points. Concentre-se em clareza, estrutura, relevância do conteúdo e formatação. Forneça um resumo breve e uma pontuação (0-100) baseada na qualidade geral. Use a segunda pessoa para se dirigir ao usuário.

            Exemplo de formato esperado:
            Resumo: [resumo breve aqui]
            Pontos Fortes:
            - [ponto forte 1]
            - [ponto forte 2]
            - [ponto forte 3]
            Pontos Fracos:
            - [ponto fraco 1]
            - [ponto fraco 2]
            - [ponto fraco 3]
            Pontuação: [número entre 0 e 100]

            Texto do CV: {text}
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Você é um assistente especialista em análise de currículos, fornecendo feedback construtivo em português."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500,
                    temperature=0.5
                )
                content = response['choices'][0]['message']['content']
                logging.info(f"Resposta do OpenAI para análise de CV: {content}")

                # Parse response using regex
                import re
                summary_match = re.search(r"Resumo:(.*?)(?=Pontos Fortes:)", content, re.DOTALL)
                strengths_match = re.search(r"Pontos Fortes:(.*?)(?=Pontos Fracos:)", content, re.DOTALL)
                weaknesses_match = re.search(r"Pontos Fracos:(.*?)(?=Pontuação:)", content, re.DOTALL)
                score_match = re.search(r"Pontuação:\s*(\d+)", content)

                summary = summary_match.group(1).strip() if summary_match else "Análise não pôde ser processada corretamente."
                strengths_text = strengths_match.group(1).strip() if strengths_match else ""
                weaknesses_text = weaknesses_match.group(1).strip() if weaknesses_match else ""
                score = int(score_match.group(1)) if score_match and 0 <= int(score_match.group(1)) <= 100 else 0

                # Convert strengths and weaknesses to lists
                strengths = [s.strip() for s in strengths_text.split('\n') if s.strip().startswith('-')]
                weaknesses = [w.strip() for w in weaknesses_text.split('\n') if w.strip().startswith('-')]

                # Ensure minimum feedback
                if not strengths:
                    strengths = ["Nenhum ponto forte identificado."]
                if not weaknesses:
                    weaknesses = ["Nenhum ponto fraco identificado."]

                return Response(
                    {
                        "summary": summary,
                        "strengths": strengths,
                        "weaknesses": weaknesses,
                        "score": score
                    },
                    status=status.HTTP_200_OK
                )

            except openai.error.OpenAIError as e:
                logging.error(f"Erro na API do OpenAI: {str(e)}")
                return Response({"error": f"Erro ao analisar o CV: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logging.error(f"Erro inesperado na análise do CV: {str(e)}")
                return Response({"error": f"Erro interno do servidor: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
            return Response({"error": f"Erro interno do servidor: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
