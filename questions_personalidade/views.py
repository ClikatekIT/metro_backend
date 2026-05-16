from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .models import QuestionPersonalidade, AnswerPersonalidade, Test
from .serializers import QuestionSerializer, AnswerSerializer, TestSerializer
import openai
from django.core.exceptions import ValidationError

from .models import Test, AnswerPersonalidade, PersonalityScore

class QuestionListView(APIView):
    def get(self, request):
        questions = QuestionPersonalidade.objects.all()
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


def calculate_personality_scores(test_id):
    RESPONSE_MAP = {
        "Discordo Muito": 1,
        "Discordo": 2,
        "Neutro": 3,
        "Concordo": 4,
        "Concordo Muito": 5
    }

    # Recupera as respostas do teste
    answers = AnswerPersonalidade.objects.filter(test=test_id)
    if not answers.exists():
        return None, {"error": "Nenhuma resposta encontrada para o teste."}

    # Inicializa os escores
    scores = {
        "Extroversao": 20,
        "Amabilidade": 14,
        "Consciencia": 14,
        "Neuroticismo": 38,
        "Abertura a Experiencia": 8,
    }

    # IDs das perguntas que subtraem pontos
    subtract_ids = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 29, 30, 32, 34, 36, 38, 39, 44, 46, 49]

    # Calcula os escores
    for answer in answers:
        try:
            value = RESPONSE_MAP[answer.answer]
        except KeyError:
            return None, {"error": f"Resposta inválida: {answer.answer}"}

        question_id = answer.question.id
        if question_id in [1, 6, 11, 16, 21, 26, 31, 36, 41, 46]:
            scores["Extroversao"] += value if question_id not in subtract_ids else -value
        elif question_id in [2, 7, 12, 17, 22, 27, 32, 37, 42, 47]:
            scores["Amabilidade"] += value if question_id not in subtract_ids else -value
        elif question_id in [3, 8, 13, 18, 23, 28, 33, 38, 43, 48]:
            scores["Consciencia"] += value if question_id not in subtract_ids else -value
        elif question_id in [4, 9, 14, 19, 24, 29, 34, 39, 44, 49]:
            scores["Neuroticismo"] += value if question_id not in subtract_ids else -value
        elif question_id in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
            scores["Abertura a Experiencia"] += value if question_id not in subtract_ids else -value

    # Salva os escores no banco de dados
    test = Test.objects.get(id=test_id)
    personality_score, created = PersonalityScore.objects.update_or_create(
        test=test,
        defaults={
            "extroversao": scores["Extroversao"],
            "amabilidade": scores["Amabilidade"],
            "consciencia": scores["Consciencia"],
            "neuroticismo": scores["Neuroticismo"],
            "abertura_experiencia": scores["Abertura a Experiencia"]
        }
    )

    return scores, None



class SaveAnswerView(APIView):
    def post(self, request):
        try:
            # Verifica se os dados são uma lista
            if isinstance(request.data, list):
                user_ids = [data.get("user_id") for data in request.data]
                if len(set(user_ids)) > 1:
                    return Response(
                        {"error": "Todos os user_ids devem ser iguais ao enviar uma lista de respostas."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user_id = user_ids[0]
            else:
                user_id = request.data.get("user_id")  # Recupera o user_id do objeto request

            # Validação do user_id
            if not user_id:
                return Response(
                    {"error": "O campo user_id é obrigatório."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"O id do usuário é: {user_id}")

            # Cria uma nova instância de Test
            try:
                test = Test.objects.create(user_id=user_id)
            except ValidationError as e:
                return Response(
                    {"error": f"Erro ao criar o teste: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            print(f"Teste criado com ID: {test.id}")

            # Atualiza os dados da requisição com o test_id e user_id
            mutable_data = request.data.copy()  # Cria uma cópia mutável dos dados
            if isinstance(mutable_data, list):
                for data in mutable_data:
                    data['test'] = test.id  # Adiciona o test_id aos dados
                    data['user'] = user_id  # Adiciona o user_id aos dados
            else:
                mutable_data['test'] = test.id  # Adiciona o test_id aos dados
                mutable_data['user'] = user_id  # Adiciona o user_id aos dados

            print(f"Dados atualizados com test_id: {mutable_data}")

            # Cria o serializer para AnswerPersonalidade
            if isinstance(mutable_data, list):
                serializer = AnswerSerializer(data=mutable_data, many=True)
            else:
                serializer = AnswerSerializer(data=mutable_data)

            # Valida e salva os dados do serializer
            if serializer.is_valid():
                serializer.save()

                # Calcula os escores de personalidade
                scores, error = calculate_personality_scores(test.id)
                if error:
                    return Response(
                        {"error": f"Erro ao calcular os escores: {error}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Retorna os escores junto com a resposta
                return Response({
                    "test": test.id,
                    "answers": serializer.data,
                    "scores": scores,
                    "message": "Respostas e escores salvos com sucesso!"
                }, status=status.HTTP_201_CREATED)

            # Registra os erros do serializer no terminal
            print(f"Erros do serializer: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Captura qualquer exceção inesperada e registra no terminal
            print(f"Erro inesperado: {str(e)}")
            return Response(
                {"error": f"Erro inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )