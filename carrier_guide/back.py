from django.db import models
from rest_framework.decorators import api_view
from rest_framework.response import Response
import openai
from .models import CognitiveTest, Question
import traceback
from django.http import JsonResponse


import os
openai.api_key = os.getenv('OPENAI_API_KEY')

@api_view(['POST'])
def generate_cognitive_test(request):

    cargo_atual = request.data.get("cargo_atual")
    cargo_desejado = request.data.get("cargo_desejado")
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')


        prompt = (
            f"Meu cargo atual é {cargo_atual} e pretendo alcançar um cargo de {cargo_desejado}.\n"
            "Gere um teste cognitivo de 5 perguntas, em Português, no nível avançado. O teste deve conter:\n"
            "- Perguntas baseadas em tabelas, focando na interpretação de dados complexos relevantes para "
            f"{cargo_desejado}, como métricas, relatórios técnicos, ou informações relacionadas.\n"
            "- Perguntas de texto simples relacionadas a habilidades cognitivas e conhecimentos necessários para "
            f"{cargo_desejado}.\n"
            "As perguntas devem ser desafiadoras, mas alinhadas ao nível de {cargo_desejado}.\n"
            "Use o formato JSON. Cada pergunta deve conter os seguintes campos:\n"
            "- 'text': O texto da pergunta.\n"
            "- 'options': Uma lista de opções de resposta para a pergunta.\n"
            "- 'correct_answer': A resposta correta para a pergunta.\n"
            "- 'metadata': Um dicionário com informações adicionais (somente necessário para perguntas baseadas em tabelas). "
            "Para tabelas, o formato deve ser:\n"
            "{'type': 'table', 'data': [['Header1', 'Header2', 'Header3', 'Header4'], ['Value1', 'Value2', 'Value3', 'Value4']]}\n"
            "Exemplo de JSON esperado:\n"
            "{\n"
            "  'summary': 'Resumo do teste',\n"
            "  'skills': ['Lista de habilidades'],\n"
            "  'test_type': 'Tipo de teste',\n"
            "  'questions': [\n"
            "    {\n"
            "      'text': 'Com base na tabela abaixo, qual opção melhor reflete a análise?',\n"
            "      'options': ['Opção A', 'Opção B', 'Opção C', 'Opção D'],\n"
            "      'correct_answer': 'Opção B',\n"
            "      'metadata': {\n"
            "        'type': 'table',\n"
            "        'data': [\n"
            "          ['Categoria', 'Indicador 1', 'Indicador 2', 'Conclusão'],\n"
            "          ['A', '50%', '30%', 'Não favorável'],\n"
            "          ['B', '80%', '90%', 'Altamente favorável'],\n"
            "          ['C', '60%', '50%', 'Moderadamente favorável']\n"
            "        ]\n"
            "      }\n"
            "    },\n"
            "    {\n"
            "      'text': 'Qual das opções abaixo é mais adequada para o seguinte cenário?',\n"
            "      'options': ['Opção 1', 'Opção 2', 'Opção 3', 'Opção 4'],\n"
            "      'correct_answer': 'Opção 3',\n"
            "      'metadata': {}\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
            max_tokens=800
        )

        content = response['choices'][0]['message']['content']
        print("Resposta do OpenAI:", content)

        # Verificar o tipo de dados recebido
        try:
            structured_data = eval(content)  # Avaliar a string JSON
            if isinstance(structured_data, list):
                raise ValueError("A resposta do OpenAI retornou uma lista, mas esperava-se um dicionário.")
        except Exception as parse_error:
            raise ValueError(f"Erro ao interpretar a resposta do OpenAI: {parse_error}")

        # Salvar no banco de dados
        cognitive_test = CognitiveTest.objects.create(
            summary=structured_data['summary'],
            skills=structured_data['skills'],
            test_type=structured_data['test_type']
        )

        for question in structured_data['questions']:
            Question.objects.create(
                test=cognitive_test,
                text=question['text'],
                options=question['options'],
                metadata=question.get('metadata'),
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
            "summary": test.summary,
            "skills": test.skills,
            "test_type": test.test_type,
            "questions": [
                {
                    "text": q.text,
                    "options": q.options,
                    "metadata": q.metadata
                }
                for q in questions
            ]
        }
        return Response(data, status=200)
    except CognitiveTest.DoesNotExist:
        return Response({"error": "Nenhum teste encontrado."}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


