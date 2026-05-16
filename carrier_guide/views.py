# views.py (código completo e corrigido com normalização no career_plan)

import json
import openai
import re
import traceback
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import CognitiveTest, Question, Test, Feedback, UserAnswer
from questions_personalidade.models import PersonalityScore
from django.conf import settings
from curriculum.models import User
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import threading
import time
import uuid

# Configuração da chave da API do OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# --- Funções Auxiliares ---
def validate_section(section_data, section_name):
    required_keys = {
        "cognitive_test_feedback": ["question_number", "feedback"],
        "personalized_career_feedback": ["description", "recommendations"],
        "recommended_courses": ["course_name", "description", "platform"],
        "career_plan": ["month_1_2", "month_3_4", "month_5", "month_6"],
        "feedback_teste_personalidade": ["Extroversão", "Amabilidade", "Consciência", "Neuroticismo", "Abertura à Experiência"]
    }
    if section_name in required_keys:
        if section_name == "cognitive_test_feedback" and not isinstance(section_data, list):
            raise ValueError(f"A seção {section_name} deve ser uma lista.")
        elif section_name == "recommended_courses" and not isinstance(section_data, list):
            raise ValueError(f"A seção {section_name} deve ser uma lista.")
        elif section_name in ["personalized_career_feedback", "career_plan", "feedback_teste_personalidade"] and not isinstance(section_data, dict):
            raise ValueError(f"A seção {section_name} deve ser um dicionário.")
        
        if section_name == "cognitive_test_feedback":
            for item in section_data:
                for key in required_keys[section_name]:
                    if key not in item or not item[key]:
                        raise ValueError(f"Chave '{key}' ausente ou vazia em um item da seção {section_name}.")
                if not isinstance(item["question_number"], int) or item["question_number"] < 1:
                    raise ValueError(f"Campo 'question_number' inválido em um item da seção {section_name}.")
        elif section_name == "recommended_courses":
            for item in section_data:
                for key in required_keys[section_name]:
                    if key not in item or not item[key]:
                        raise ValueError(f"Chave '{key}' ausente ou vazia em um item da seção {section_name}.")
        else:
            for key in required_keys[section_name]:
                if key not in section_data or not section_data[key]:
                    raise ValueError(f"Chave '{key}' ausente ou vazia na seção {section_name}.")
    return True

def extract_json_from_response(raw_response):
    try:
        clean_response = re.sub(r'```json\s*', '', raw_response)
        clean_response = re.sub(r'```\s*$', '', clean_response)
        clean_response = clean_response.strip()
        json_match = re.search(r'(\{.*\}|\[.*\])', clean_response, re.DOTALL)
        if not json_match:
            raise ValueError("JSON não encontrado na resposta.")
        json_part = json_match.group(0).strip()
        return json.loads(json_part)
    except json.JSONDecodeError as e:
        raise ValueError(f"Erro ao interpretar a resposta do OpenAI: {e}\nResposta bruta: {raw_response}")

# --- Funções de Geração de Feedback ---
def gerar_cognitive_test_feedback(passo_feedback, scores_summary, cargo_atual, cargo_desejado, habilidades, max_retries=3):
    prompt = f"""
    Você é um especialista em avaliação de testes técnicos e análise de carreira. Sua tarefa é gerar apenas a seção 'cognitive_test_feedback' com base nas respostas do usuário fornecidas abaixo. Siga estas instruções:

    - Analise cada pergunta individualmente, com base nas respostas fornecidas no JSON 'passo_feedback' (um array de objetos contendo 'question_number', 'text', 'options', 'metadata', 'user_answer', 'correct_answer', e 'is_correct').
    - Para cada pergunta:
      - Confirme se a resposta está correta/incorreta e explique por que, usando 'text', 'options', 'user_answer', 'correct_answer'.
      - Se 'metadata' contiver uma tabela (type: 'table'), analise os dados da tabela e explique como eles levam à resposta correta.
      - Conecte a análise às responsabilidades específicas do cargo desejado ({cargo_desejado}), explicando como a habilidade avaliada (ou sua falta) impacta o desempenho nesse cargo.
      - Relacione o desempenho na pergunta aos traços de personalidade (como extroversão, conscienciosidade, abertura à experiência, etc.), explicando detalhadamente como esses traços influenciaram a resposta.
      - Se a resposta estiver errada, forneça uma sugestão prática e detalhada para melhorar essa habilidade, como "analise relatórios financeiros semanais para melhorar a interpretação de dados".
    - Use um tom profissional, empático e motivador, incentivando o candidato a melhorar enquanto reconhece suas forças.
    - Retorne um JSON válido com a chave 'cognitive_test_feedback', contendo uma lista de objetos, cada um com:
      - 'question_number': Número da pergunta (inteiro, começando em 1).
      - 'feedback': Texto detalhado do feedback.
      - 'correct': Booleano indicando se a resposta do usuário está correta (true/false).

    Respostas do usuário:
    {passo_feedback}

    Escores de personalidade:
    {scores_summary}

    Cargo atual:
    {cargo_atual}

    Cargo desejado:
    {cargo_desejado}

    Habilidades do usuário:
    {habilidades}

    Responda APENAS com o JSON, sem texto adicional ou marcadores de código:
    """
    
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            content = response['choices'][0]['message']['content'].strip()
            print(f"Resposta do OpenAI para cognitive_test_feedback: {content}")
            
            data = extract_json_from_response(content)
            if "cognitive_test_feedback" not in data:
                raise ValueError("Chave 'cognitive_test_feedback' não encontrada na resposta.")
            
            validate_section(data["cognitive_test_feedback"], "cognitive_test_feedback")
            return data["cognitive_test_feedback"]
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para cognitive_test_feedback: {str(e)}")
            if attempt == max_retries - 1:
                return {"error": f"Falha após {max_retries} tentativas: {str(e)}"}
    return {"error": "Falha ao gerar cognitive_test_feedback."}

def gerar_personalized_career_feedback(cargo_atual, cargo_desejado, habilidades, scores_summary, max_retries=3):
    prompt = f"""
    Você é um especialista em desenvolvimento de carreira. Sua tarefa é gerar apenas a seção 'personalized_career_feedback' com base nos dados fornecidos abaixo. Siga estas instruções:

    - Analise o cargo atual ({cargo_atual}), o cargo desejado ({cargo_desejado}) e as habilidades do usuário ({habilidades}).
    - Considere os escores de personalidade fornecidos ({scores_summary}) para personalizar o feedback, destacando como traços como extroversão, conscienciosidade, etc., podem influenciar a transição de carreira.
    - Identifique as principais lacunas entre o cargo atual e o desejado, sugerindo como as habilidades atuais podem ser aproveitadas ou desenvolvidas.
    - Forneça um tom motivador e profissional, oferecendo pelo menos 2-3 recomendações práticas (ex.: "Participe de workshops de liderança" ou "Busque mentoria em projetos de [habilidade]").
    - Retorne um JSON válido com a chave 'personalized_career_feedback', contendo um objeto com as chaves 'description' e 'recommendations' (uma lista de recomendações).

    Responda APENAS com o JSON, sem texto adicional ou marcadores de código:
    """
    
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            content = response['choices'][0]['message']['content'].strip()
            print(f"Resposta do OpenAI para personalized_career_feedback: {content}")
            
            data = extract_json_from_response(content)
            if "personalized_career_feedback" not in data:
                raise ValueError("Chave 'personalized_career_feedback' não encontrada na resposta.")
            
            feedback = data["personalized_career_feedback"]
            validate_section(feedback, "personalized_career_feedback")
            return feedback
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para personalized_career_feedback: {str(e)}")
            if attempt == max_retries - 1:
                return {"error": f"Falha após {max_retries} tentativas: {str(e)}"}
    return {"error": "Falha ao gerar personalized_career_feedback."}

def gerar_recommended_courses(cargo_atual, cargo_desejado, habilidades, scores_summary, max_retries=3):
    prompt = f"""
    Você é um especialista em desenvolvimento de carreira. Sua tarefa é gerar apenas a seção 'recommended_courses' com base nos dados fornecidos abaixo. Siga estas instruções:

    - Sugira cinco cursos relevantes para abordar as lacunas de habilidades identificadas nas habilidades do usuário ({habilidades}) e nos escores de personalidade ({scores_summary}), alinhados com a transição do cargo atual ({cargo_atual}) para o cargo desejado ({cargo_desejado}).
    - Priorize cursos nas áreas de liderança, análise de dados, estratégia, negociação e networking.
    - Alinhe as sugestões com as tendências atuais da indústria.
    - Para cada curso, inclua:
      - 'course_name': Nome do curso.
      - 'description': Descrição detalhada de como o curso ajudará o candidato a alcançar o cargo desejado, com exemplos práticos.
      - 'platform': Plataforma onde o curso pode ser encontrado (ex.: Udemy, Coursera, LinkedIn Learning, edX).
    - Use um tom profissional, empático e motivador.
    - Retorne um JSON válido com a chave 'recommended_courses', contendo uma lista de cinco cursos.

    Responda APENAS com o JSON, sem texto adicional ou marcadores de código:
    """
    
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            content = response['choices'][0]['message']['content'].strip()
            print(f"Resposta do OpenAI para recommended_courses: {content}")
            
            data = extract_json_from_response(content)
            if "recommended_courses" not in data:
                raise ValueError("Chave 'recommended_courses' não encontrada na resposta.")
            
            validate_section(data["recommended_courses"], "recommended_courses")
            return data["recommended_courses"]
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para recommended_courses: {str(e)}")
            if attempt == max_retries - 1:
                return {"error": f"Falha após {max_retries} tentativas: {str(e)}"}
    return {"error": "Falha ao gerar recommended_courses."}

def gerar_career_plan(cargo_atual, cargo_desejado, habilidades, scores_summary, max_retries=3):
    prompt = f"""
    Você é um especialista em desenvolvimento de carreira. Sua tarefa é gerar apenas a seção 'career_plan' com base nos dados fornecidos abaixo. Siga estas instruções:

    - Crie um plano de carreira de 6 meses para a transição do cargo atual ({cargo_atual}) para o cargo desejado ({cargo_desejado}), considerando as habilidades do usuário ({habilidades}) e os escores de personalidade ({scores_summary}).
    - Estruture o plano em quatro fases:
      - month_1_2: Ações imediatas para desenvolver liderança e pensamento estratégico, como completar cursos, iniciar projetos e construir relacionamentos com tomadores de decisão.
      - month_3_4: Fortalecer habilidades de liderança, preparar-se para negociações salariais (usando benchmarks de mercado) e explorar oportunidades de promoção.
      - month_5: Buscar promoções internas ou explorar oportunidades externas, revisando benchmarks salariais e praticando técnicas de negociação.
      - month_6: Posicionar-se estrategicamente na nova função, garantindo uma transição bem-sucedida e aumentando a visibilidade em discussões de alto impacto.
    - Use um tom profissional, empático e motivador, com ações específicas e práticas.
    - Retorne um JSON válido com a chave 'career_plan', contendo um objeto com as chaves 'month_1_2', 'month_3_4', 'month_5', 'month_6'.
    - Cada valor deve ser uma lista de strings (ex.: ["Ação 1: Complete o curso X.", "Ação 2: Inicie projeto Y."]). Não use objetos aninhados.

    Responda APENAS com o JSON, sem texto adicional ou marcadores de código:
    """
    
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            content = response['choices'][0]['message']['content'].strip()
            print(f"Resposta do OpenAI para career_plan: {content}")
            
            data = extract_json_from_response(content)
            if "career_plan" not in data:
                raise ValueError("Chave 'career_plan' não encontrada na resposta.")
            
            # Normalização: Transforma cada valor em uma lista de strings
            def normalize_career_plan(career_plan):
                normalized = {}
                for key, value in career_plan.items():
                    if isinstance(value, dict):
                        # Casos específicos
                        if "actions" in value:
                            normalized[key] = value["actions"] if isinstance(value["actions"], list) else [str(value["actions"])]
                        elif "goal" in value and "description" in value:
                            normalized[key] = [f"Meta: {value['goal']}", f"Descrição: {value['description']}"]
                        else:
                            # Fallback genérico para qualquer dict: converte em lista de "Chave: Valor"
                            normalized[key] = [f"{sub_key}: {sub_value}" for sub_key, sub_value in value.items()]
                    elif isinstance(value, list):
                        normalized[key] = [str(item) for item in value]  # Garante que itens sejam strings
                    elif isinstance(value, (str, int, float)):
                        normalized[key] = [str(value)]  # Converte para lista com um item
                    else:
                        print(f"Aviso: Valor inesperado para {key}: {value}. Convertendo para string.")
                        normalized[key] = [str(value)]  # Fallback para tipos inesperados
                    # Checagem extra: Garante que não seja vazia
                    if not normalized[key]:
                        raise ValueError(f"Valor normalizado para {key} está vazio.")
                return normalized
            
            plan = normalize_career_plan(data["career_plan"])
            validate_section(plan, "career_plan")
            return plan
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para career_plan: {str(e)}")
            if attempt == max_retries - 1:
                return {"error": f"Falha após {max_retries} tentativas: {str(e)}"}
    return {"error": "Falha ao gerar career_plan."}

def gerar_feedback_teste_personalidade(scores_summary, cargo_atual, cargo_desejado, max_retries=3):
    prompt = f"""
    Você é um especialista em desenvolvimento de carreira. Sua tarefa é gerar apenas a seção 'feedback_teste_personalidade' com base nos dados fornecidos abaixo. Siga estas instruções:

    - Analise os traços de personalidade fornecidos em 'scores_summary' ({scores_summary}) e sua relevância para o cargo atual ({cargo_atual}) e o cargo desejado ({cargo_desejado}).
    - Para cada traço (Extroversão, Amabilidade, Consciência, Neuroticismo, Abertura à Experiência):
      - Destaque a força ou desafio que o traço representa com base em seu escore (ex.: alta Extroversão é um ativo para liderança, Neuroticismo moderado sugere bom gerenciamento de estresse, mas risco de sobrecarga).
      - Conecte o traço a implicações específicas na carreira, como visibilidade, pensamento estratégico ou colaboração em equipe, com exemplos relevantes para o cargo desejado.
      - Forneça uma sugestão prática por traço para aproveitar forças ou mitigar fraquezas (ex.: "Use sua alta Extroversão para fazer networking com líderes seniores" ou "Pratique delegação para gerenciar Neuroticismo moderado").
    - Use um tom profissional, empático e motivador.
    - Retorne um JSON válido com a chave 'feedback_teste_personalidade', contendo um objeto com os traços como chaves e objetos com 'score' e 'feedback'.

    Responda APENAS com o JSON, sem texto adicional ou marcadores de código:
    """
    
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=1500,
                temperature=0.3
            )
            content = response['choices'][0]['message']['content'].strip()
            print(f"Resposta do OpenAI para feedback_teste_personalidade: {content}")
            
            data = extract_json_from_response(content)
            if "feedback_teste_personalidade" not in data:
                raise ValueError("Chave 'feedback_teste_personalidade' não encontrada na resposta.")
            
            validate_section(data["feedback_teste_personalidade"], "feedback_teste_personalidade")
            return data["feedback_teste_personalidade"]
        except Exception as e:
            print(f"Tentativa {attempt + 1} falhou para feedback_teste_personalidade: {str(e)}")
            if attempt == max_retries - 1:
                return {"error": f"Falha após {max_retries} tentativas: {str(e)}"}
    return {"error": "Falha ao gerar feedback_teste_personalidade."}

def generate_feedback_in_background(passo_feedback, scores_summary, cargo_atual, cargo_desejado, habilidades, cognitive_test, user):
    """
    Função que gera feedback em etapas e salva incrementalmente no banco de dados.
    """
    try:
        print(f"Iniciando geração de feedback para teste {cognitive_test.id}")
        
        # Gerar e salvar cognitive_test_feedback primeiro
        cognitive_feedback = gerar_cognitive_test_feedback(
            passo_feedback, scores_summary, cargo_atual, cargo_desejado, habilidades
        )
        
        if isinstance(cognitive_feedback, dict) and "error" in cognitive_feedback:
            print(f"Erro na geração de cognitive_test_feedback: {cognitive_feedback['error']}")
            feedback_obj = Feedback.objects.create(
                cognitive_test=cognitive_test,
                user=user,
                feedback_data={"cognitive_test_feedback": {"error": cognitive_feedback['error']}}
            )
            return
        
        # Salvar apenas cognitive_test_feedback inicialmente
        feedback_obj = Feedback.objects.create(
            cognitive_test=cognitive_test,
            user=user,
            feedback_data={"cognitive_test_feedback": cognitive_feedback}
        )
        print(f"Feedback cognitivo gerado e salvo para o teste {cognitive_test.id}, ID: {feedback_obj.id}")

        # Gerar os outros feedbacks em segundo plano
        career_feedback = gerar_personalized_career_feedback(
            cargo_atual, cargo_desejado, habilidades, scores_summary
        )
        if isinstance(career_feedback, dict) and "error" in career_feedback:
            print(f"Erro na geração de personalized_career_feedback: {career_feedback['error']}")
        else:
            feedback_obj.feedback_data["personalized_career_feedback"] = career_feedback
            feedback_obj.save()
            print(f"Feedback de carreira gerado e salvo para o teste {cognitive_test.id}, ID: {feedback_obj.id}")

        recommended_courses = gerar_recommended_courses(
            cargo_atual, cargo_desejado, habilidades, scores_summary
        )
        if isinstance(recommended_courses, dict) and "error" in recommended_courses:
            print(f"Erro na geração de recommended_courses: {recommended_courses['error']}")
        else:
            feedback_obj.feedback_data["recommended_courses"] = recommended_courses
            feedback_obj.save()
            print(f"Cursos recomendados gerados e salvos para o teste {cognitive_test.id}, ID: {feedback_obj.id}")

        career_plan = gerar_career_plan(
            cargo_atual, cargo_desejado, habilidades, scores_summary
        )
        if isinstance(career_plan, dict) and "error" in career_plan:
            print(f"Erro na geração de career_plan: {career_plan['error']}")
        else:
            feedback_obj.feedback_data["career_plan"] = career_plan
            feedback_obj.save()
            print(f"Plano de carreira gerado e salvo para o teste {cognitive_test.id}, ID: {feedback_obj.id}")

        personality_feedback = gerar_feedback_teste_personalidade(
            scores_summary, cargo_atual, cargo_desejado
        )
        if isinstance(personality_feedback, dict) and "error" in personality_feedback:
            print(f"Erro na geração de feedback_teste_personalidade: {personality_feedback['error']}")
        else:
            feedback_obj.feedback_data["feedback_teste_personalidade"] = personality_feedback
            feedback_obj.save()
            print(f"Feedback de personalidade gerado e salvo para o teste {cognitive_test.id}, ID: {feedback_obj.id}")
        
    except Exception as e:
        print(f"Erro na geração de feedback em segundo plano: {str(e)}")
        print(traceback.format_exc())
        feedback_obj.feedback_data["error"] = str(e)
        feedback_obj.save()

@csrf_exempt
def feedback_teste(request):
    """
    View que lida com geração e recuperação de feedback usando polling com suporte a feedback parcial.
    """
    try:
        if request.method == 'POST':
            print("Recebendo as respostas do usuário para iniciar a geração de feedback...")
            
            if hasattr(request, 'data') and request.data:
                data = request.data
            else:
                data = json.loads(request.body.decode('utf-8'))
            
            user_id = data.get('user_id')
            user_answers = data.get('respostasDoUsuario')
            teste_id = data.get('testeID')
            habilidades = data.get('habilidades')

            if not user_id or not user_answers or not teste_id:
                print("Dados insuficientes para gerar o feedback.")
                return JsonResponse({
                    "error": "Dados insuficientes para gerar o feedback. user_id, respostasDoUsuario e testeID são obrigatórios."
                }, status=400)

            try:
                cognitive_test = CognitiveTest.objects.get(id=teste_id)
            except CognitiveTest.DoesNotExist:
                return JsonResponse({"error": "Teste cognitivo não encontrado."}, status=404)

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": f"Usuário com ID {user_id} não encontrado."}, status=404)

            try:
                personality_score = PersonalityScore.objects.get(test_id=cognitive_test.id_teste_personalidade_id)
                scores = {
                    "Extroversão": personality_score.extroversao,
                    "Amabilidade": personality_score.amabilidade,
                    "Consciência": personality_score.consciencia,
                    "Neuroticismo": personality_score.neuroticismo,
                    "Abertura à Experiência": personality_score.abertura_experiencia
                }
            except PersonalityScore.DoesNotExist:
                print("Escores de personalidade não encontrados.")
                return JsonResponse({"error": "Escores de personalidade não encontrados para este teste."}, status=404)

            passo_feedback_data = []
            questions = cognitive_test.questions.all()
            for index, question in enumerate(questions):
                user_answer = user_answers.get(str(index))
                if user_answer is None:
                    continue

                correct = question.correct_answer
                is_correct = user_answer == correct

                passo_feedback_data.append({
                    "question_number": index + 1,
                    "text": question.text,
                    "options": question.options,
                    "metadata": question.metadata if question.metadata else {},
                    "user_answer": user_answer,
                    "correct_answer": correct,
                    "is_correct": is_correct
                })

            passo_feedback = json.dumps(passo_feedback_data, ensure_ascii=False)
            scores_summary = "\n".join([f"- {k}: {v}" for k, v in scores.items()])

            existing_feedback = Feedback.objects.filter(cognitive_test=cognitive_test, user=user).first()
            if existing_feedback:
                existing_feedback.delete()

            threading.Thread(target=generate_feedback_in_background, args=(
                passo_feedback, scores_summary, cognitive_test.cargo_atual, 
                cognitive_test.cargo_desejado, habilidades, cognitive_test, user
            )).start()
            
            return JsonResponse({"message": "Geração de feedback iniciada.", "status": "processing"}, status=202)

        elif request.method == 'GET':
            teste_id = request.GET.get('testeID')
            if not teste_id:
                return JsonResponse({"error": "testeID é obrigatório para requisições GET."}, status=400)

            try:
                cognitive_test = CognitiveTest.objects.get(id=teste_id)
            except CognitiveTest.DoesNotExist:
                return JsonResponse({"error": "Teste não encontrado."}, status=404)

            feedback = Feedback.objects.filter(cognitive_test=cognitive_test).order_by('-created_at').first()
            
            if feedback and feedback.feedback_data:
                response_data = {
                    'status': 'completed' if all(k in feedback.feedback_data for k in [
                        'cognitive_test_feedback', 'personalized_career_feedback', 
                        'recommended_courses', 'career_plan', 'feedback_teste_personalidade'
                    ]) else 'partial',
                    'cognitive_test_feedback': feedback.feedback_data.get('cognitive_test_feedback', []),
                    'personalized_career_feedback': feedback.feedback_data.get('personalized_career_feedback', {}),
                    'recommended_courses': feedback.feedback_data.get('recommended_courses', []),
                    'career_plan': feedback.feedback_data.get('career_plan', {}),
                    'feedback_teste_personalidade': feedback.feedback_data.get('feedback_teste_personalidade', {})
                }
                return JsonResponse(response_data)
            else:
                return JsonResponse({
                    'status': 'pending',
                    'message': 'Feedback ainda não foi gerado. Aguardando...'
                })

    except Exception as e:
        print(f"Erro no feedback_teste view: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": "Erro interno do servidor ao processar a requisição."}, status=500)

# --- Outras Views (mantidas as mesmas) ---
@api_view(['POST'])
def generate_cognitive_test(request):
    cargo_atual = request.data.get("cargo_atual")
    cargo_desejado = request.data.get("cargo_desejado")
    id_teste_personalidade = Test.objects.get(id=request.data.get("id_teste_personalidade"))

    try:
        prompt = (
            f"Meu cargo atual é {cargo_atual} e pretendo alcançar um cargo de {cargo_desejado}.\n"
            "Gere um teste cognitivo de 5 perguntas, em Português, no nível avançado. O teste deve conter:\n"
            "- Perguntas baseadas em tabelas, focando na interpretação de dados complexos relevantes para "
            f"{cargo_desejado}, como métricas, relatórios técnicos, ou informações relacionadas.\n"
            "- Perguntas de texto simples relacionadas a habilidades cognitivas e conhecimentos necessários para "
            f"{cargo_desejado}.\n"
        )

        if "engenharia informática" in cargo_desejado.lower() or "desenvolvedor" in cargo_desejado.lower():
            prompt += (
                "- Uma pergunta sobre análise de código, onde um trecho de código é fornecido e o usuário precisa identificar "
                "o erro ou a saída do código.\n"
            )

        prompt += (
            "As perguntas devem ser desafiadoras, mas alinhadas ao nível de {cargo_desejado}.\n"
            "Use o formato JSON. Cada pergunta deve conter os seguintes campos:\n"
            "- 'text': O texto da pergunta.\n"
            "- 'options': Uma lista de opções de resposta para a pergunta.\n"
            "- 'correct_answer': A resposta correta para a pergunta.\n"
            "- 'metadata': Um dicionário com informações adicionais (somente necessário para perguntas baseadas em tabelas e análise de código). "
            "Para tabelas, o formato deve ser:\n"
            "{'type': 'table', 'data': [['Header1', 'Header2', 'Header3', 'Header4'], ['Value1', 'Value2', 'Value3', 'Value4']]}\n"
            "Exemplo de JSON esperado:\n"
            "{\n"
            "  \"summary\": \"Resumo do teste\",\n"
            "  \"skills\": [\"Lista de habilidades\"],\n"
            "  \"test_type\": \"Tipo de teste\",\n"
            "  \"questions\": [\n"
            "    {\n"
            "      \"text\": \"Com base na tabela abaixo, qual opção melhor reflete a análise?\",\n"
            "      \"options\": [\"Opção A\", \"Opção B\", \"Opção C\", \"Opção D\"],\n"
            "      \"correct_answer\": \"Opção B\",\n"
            "      \"metadata\": {\n"
            "        \"type\": \"table\",\n"
            "        \"data\": [\n"
            "          [\"Categoria\", \"Indicador 1\", \"Indicador 2\", \"Conclusão\"],\n"
            "          [\"A\", \"50%\", \"30%\", \"Não favorável\"],\n"
            "          [\"B\", \"80%\", \"90%\", \"Altamente favorável\"],\n"
            "          [\"C\", \"60%\", \"50%\", \"Moderadamente favorável\"]\n"
            "        ]\n"
            "      }\n"
            "    },\n"
            "    {\n"
            "      \"text\": \"Qual das opções abaixo é mais adequada para o seguinte cenário?\",\n"
            "      \"options\": [\"Opção 1\", \"Opção 2\", \"Opção 3\", \"Opção 4\"],\n"
            "      \"correct_answer\": \"Opção 3\",\n"
            "      \"metadata\": {}\n"
            "    },\n"
            "    {\n"
            "      \"text\": \"Analise o seguinte trecho de código e identifique o problema\",\n"
            "      \"options\": [\"Problema de sintaxe\", \"Problema de lógica\", \"Problema de performance\", \"Nenhum problema\"],\n"
            "      \"correct_answer\": \"Problema de lógica\",\n"
            "      \"metadata\": {\n"
            "        \"type\": \"code\",\n"
            "        \"code\": \"def soma(a, b):\\n    return a - b\"\n"
            "      }\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=2000
        )

        content = response['choices'][0]['message']['content'].strip()
        print("Resposta do OpenAI:", content)

        try:
            structured_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao interpretar a resposta do OpenAI: {e}\nResposta bruta: {content}")

        cognitive_test = CognitiveTest.objects.create(
            summary=structured_data['summary'],
            skills=structured_data['skills'],
            test_type=structured_data['test_type'],
            id_teste_personalidade=id_teste_personalidade,
            cargo_atual=cargo_atual,
            cargo_desejado=cargo_desejado
        )

        for question in structured_data['questions']:
            Question.objects.create(
                test=cognitive_test,
                text=question['text'],
                options=question['options'],
                metadata=question.get('metadata', {}),
                correct_answer=question['correct_answer']
            )

        return Response({"message": "Teste gerado e armazenado com sucesso."}, status=200)

    except Exception as e:
        print("Erro:", e)
        print("Detalhes do erro:", traceback.format_exc())
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def fetch_cognitive_test(request):
    try:
        test = CognitiveTest.objects.latest('created_at')
        questions = test.questions.all()
        data = {
            "id": test.id,
            "summary": test.summary,
            "skills": test.skills,
            "test_type": test.test_type,
            "questions": [
                {
                    "text": q.text,
                    "options": q.options,
                    "metadata": q.metadata,
                    "correct_answer": q.correct_answer,
                }
                for q in questions
            ]
        }
        return Response(data, status=200)
    except CognitiveTest.DoesNotExist:
        return Response({"error": "Nenhum teste encontrado."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def fetch_user_feedbacks(request):
    try:
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "user_id é obrigatório."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuário com o ID fornecido não encontrado."}, status=404)

        feedbacks = Feedback.objects.filter(user=user).select_related('cognitive_test')
        data = [
            {
                "id": feedback.id,
                "test_id": feedback.cognitive_test.id,
                "test_summary": feedback.cognitive_test.summary,
                "cargo_atual": feedback.cognitive_test.cargo_atual,
                "cargo_desejado": feedback.cognitive_test.cargo_desejado,
                "feedback_data": feedback.feedback_data,
                "created_at": feedback.created_at,
                "test_details": {
                    "skills": feedback.cognitive_test.skills,
                    "test_type": feedback.cognitive_test.test_type,
                    "questions": [
                        {
                            "id": question.id,
                            "text": question.text,
                            "options": question.options,
                            "metadata": question.metadata,
                            "correct_answer": question.correct_answer,
                            "user_answer": (
                                user_answer.user_answer
                                if (user_answer := question.user_answers.filter(feedback=feedback).first())
                                else None
                            )
                        }
                        for question in feedback.cognitive_test.questions.all()
                    ]
                }
            }
            for feedback in feedbacks
        ]
        return Response(data, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['POST'])
def check_personality_test(request):
    try:
        user_id = request.data.get('user_id')
        if not user_id:
            print("user_id é obrigatório.")
            return Response({"error": "user_id é obrigatório."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            print("Usuário com o ID fornecido não encontrado")
            return Response({"error": "Usuário com o ID fornecido não encontrado."}, status=404)

        personality_tests = Test.objects.filter(user=user).order_by('-created_at')
        if not personality_tests.exists():
            print("Nenhum teste de personalidade encontrado.")
            return Response({"has_test": False, "message": "Nenhum teste de personalidade encontrado."}, status=200)

        latest_test = personality_tests.first()
        return Response({
            "has_test": True,
            "test_id": latest_test.id,
            "created_at": latest_test.created_at,
            "message": "Teste de personalidade encontrado."
        }, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)