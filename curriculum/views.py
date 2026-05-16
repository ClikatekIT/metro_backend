from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import APIView
from rest_framework import status
from portalsdk import APIContext, APIMethodType, APIRequest
from django.views.decorators.csrf import  ensure_csrf_cookie
from django.http import JsonResponse
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime
from social_django.utils import psa
from pprint import pprint
import logging
import re

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

import braintree
import openai
import requests
import paypalrestsdk

from .models import (
    User,
    JobDescription,
    CV,
    Transacao,
    PersonalInfo,
    Credit,
)
from .serializers import (
    UserSerializer,
    PersonalInfoSerializer,
    UserDetailSerializer,
    CVSerializer,
    TransacaoSerializer,
    CreditSerializer,
    JobDescriptionSerializer,
    EmailTokenObtainPairSerializer,
    UsoCreditoSerializer
)


class CheckEmailExistsView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        exists = User.objects.filter(email__iexact=email).exists()
        return Response({"exists": exists})


class UserLoggedInView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_data = UserSerializer(user).data

        # Aqui, pegue o primeiro CV do usuário (ou defina uma lógica para escolher o CV correto)
        cv = user.cvs.first()  # ou algum `filter(...).first()` dependendo da lógica

        if cv and hasattr(cv, "personal_info"):
            user_data["personal_info"] = PersonalInfoSerializer(cv.personal_info).data
        else:
            user_data["personal_info"] = None

        return Response(user_data)



class UserViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]  # Permite a criação de usuário sem autenticação
        return super().get_permissions()

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all().order_by(
                "created_at"
            )  # Admins podem ver todos os usuários
        return User.objects.filter(
            id=self.request.user.id
        )  # Usuário vê apenas a si mesmo

    def get_serializer_class(self):
        # Define o serializer de acordo com o tipo de requisição
        if self.action == "retrieve":
            return UserDetailSerializer
        return UserSerializer

    def perform_create(self, serializer):
        # Criação do usuário com a lógica do Serializer
        serializer.save()

    def update(self, request, *args, **kwargs):
        """
        Atualiza os dados do usuário especificado.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Se a senha for modificada, garante a criptografia
        if "password" in request.data:
            user.set_password(request.data["password"])
            user.save()

        return Response(serializer.data)


class PersonalInfoViweSet(ModelViewSet):
    serializer_class = PersonalInfoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        if self.request.user.is_staff:
            return PersonalInfo.objects.all().order_by("created_at")
        return PersonalInfo.objects.filter(cv__user=self.request.user).order_by("created_at")


# CV ViewSet
class CVViewSet(ModelViewSet):
    # queryset = CV.objects.all().order_by("created_at")
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff:
            return CV.objects.all().order_by("created_at")
        return CV.objects.filter(user=self.request.user).order_by("created_at")


class TransacaoViewSet(ModelViewSet):
    queryset = Transacao.objects.all()
    serializer_class = TransacaoSerializer
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        # Bloquear criação de transações manualmente
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        # Bloquear atualização de transações
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        # Bloquear atualização parcial
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        # Bloquear exclusão de transações
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

# Credit ViewSet
class CreditViewSet(ModelViewSet):
    queryset = Credit.objects.all()
    serializer_class = CreditSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        # Bloquear listagem de créditos
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, *args, **kwargs):
        # Bloquear detalhes de crédito
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    
class UsoCreditoViewSet(ModelViewSet):
    serializer_class = UsoCreditoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Sem listagem para `UsoCredito`
        return []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['user'] = request.user
        transacao = serializer.save()
        return Response(
            {"message": "Crédito usado com sucesso", "transacao": transacao.id},
            status=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def retrieve(self, request, *args, **kwargs):
        return Response({"detail": "Método não permitido."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class JobDescriptionViewSet(ModelViewSet):
    serializer_class = JobDescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = JobDescription.objects.all().order_by("created_at")
        queryset = queryset.prefetch_related(
            "experience", "education", "language", "software"
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def perform_create(self, serializer):
        # Define automaticamente o usuário autenticado como dono da JobDescription
        serializer.save(user=self.request.user)


@ensure_csrf_cookie
def get_csrf_token(request):
    return JsonResponse({"detail": "CSRF cookie set"})

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    
    
User = get_user_model()
class GoogleTokenObtainPairView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response({"detail": "Token não enviado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Valida o token no Google
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Procura ou cria o usuário
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"email": email, "name": name}
            )

            if created:
                user.is_active = True
                user.save()

            # Gera tokens JWT
            refresh = RefreshToken.for_user(user)

            return Response({
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_staff": user.is_staff,
                "is_active": user.is_active,
            })

        except ValueError:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)


openai.api_key = settings.OPENAI_API_KEY

class GenerateTasksView(APIView):
    permission_classes = [
        IsAuthenticated
    ]  # Garante que só usuários autenticados acessem

    def post(self, request):
        try:
            role = request.data.get("role", "")
            associated_roles = request.data.get("associatedRoles", [])
            user_tasks = request.data.get("description", [])

            if not role:
                return Response(
                    {"error": "Cargo é obrigatório"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not user_tasks:
                return Response(
                    {"error": "As tarefas do usuário são obrigatórias"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            prompt = f"""
Você é um especialista em descrição de cargos e redação de atribuições profissionais com ampla experiência 
em recursos humanos e organização empresarial.

Estamos refinando a descrição de cargo para a posição de {role}, que interage principalmente com as áreas de {', '.join(associated_roles)}.

Tarefas actuais inseridas pelo usuário:
{chr(10).join(f"- {task}" for task in user_tasks)}

Instruções para revisão:
- Reescreva cada tarefa de forma objetiva, específica e profissional.
- Use terminologia técnica adequada ao cargo e evite generalidades.
- Mantenha linguagem formal e orientada a ações (verbo no infinitivo).
- Acrescente até 3 tarefas críticas que possam estar faltando.
- Considere competências transversais e colaboração interdepartamental.
- Mantenha o escopo alinhado com {role}, destacando conexões com {', '.join(associated_roles)}.

Formato de saída:
- Liste apenas as tarefas, sem bullets, sem traços, sem numeração ou categorias.
- Cada tarefa em uma nova linha.
- Nenhum título, explicação ou texto adicional antes ou depois da lista.

Devolva APENAS a lista final melhorada no formato indicado.
"""

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=700,
            )

            improved_tasks = response.choices[0].message["content"]

            return Response({"improvedTasks": improved_tasks}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GenerateKeyWordsView(APIView):  # <-- Converte para ViewSet
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            role = request.data.get("role", "")
            description = request.data.get("description", "")

            if not role:
                return Response(
                    {"error": "Cargo é obrigatório"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not description:
                return Response(
                    {"error": "Descrição da vaga é obrigatória"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            prompt = f"""
            Extraia de 5 a 10 palavras-chave relevantes da seguinte descrição de vaga para o cargo de {role}.

            As palavras-chave devem ser:
            - Focadas em habilidades, ferramentas, tecnologias, responsabilidades e qualificações técnicas.
            - Palavras individuais, sem frases completas e quebradas apos cada espaço encontrado, ponto e virgula ou barra n.
            - Retornadas em formato de array JSON: ["palavra1", "palavra2", ...]

            Evite palavras genéricas como "trabalho", "empresa", "responsável". Foque apenas em termos técnicos e específicos.

            Descrição da vaga:
            {description}
            """


            # Chama a API OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
            )

            keywords = response.choices[0].message.content.strip().split(", ")
            return Response({"keywords": keywords}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# Traducao
def traduzir_texto(texto, idioma_alvo="en"):
    
    prompt = f"""
    Você é um tradutor profissional. Traduza o texto abaixo para o idioma {idioma_alvo}.
    Se o texto for um nome próprio, nome de instituição, local ou palavra sem tradução, 
    mantenha exatamente como está, sem explicações ou observações.
    
    {texto}
    """
    try:
        response = openai.ChatCompletion.create(
           model="gpt-4",
           messages=[{"role": "user", "content": prompt}],
           max_tokens=500, 
           temperature=0.7 
        )
        
        # Agora a tradução é extraída corretamente
        traduzido = response['choices'][0]['message']['content'].strip()
        return traduzido
    except Exception as e:
        print(f"Erro ao traduzir o texto: {e}")
        return texto  # Retorna o texto original caso ocorra erro
    
class TraduzirCV(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        # Recebe os dados do CV enviados pelo frontend
        cv_data = request.data

        try:
            # Tradução dos textos do CV
            cv_data["description"] = traduzir_texto(cv_data["description"], idioma_alvo="en")
            
            if "experiences" in cv_data:
                for experience in cv_data["experiences"]:
                    experience["description"] = traduzir_texto(experience["description"], idioma_alvo="en")
                    experience["job_title"] = traduzir_texto(experience["job_title"], idioma_alvo="en")
                    
                    if "associated_title" in experience:
                        experience["associated_title"] = [
                        traduzir_texto(title, idioma_alvo="en") for title in experience["associated_title"]
                     ]
            if "internships" in cv_data:
                for internship in cv_data["internships"]:
                    internship["description"] = traduzir_texto(internship["description"], idioma_alvo="en")
                    internship["job_title"] = traduzir_texto(internship["job_title"], idioma_alvo="en")
                    
                    if "associated_title" in internship:
                        internship["associated_title"] = [
                        traduzir_texto(title, idioma_alvo="en") for title in internship["associated_title"]
                     ]
                        
            if "educations" in cv_data:
                for education in cv_data["educations"]:
                    education["institution"] = traduzir_texto(education["institution"], idioma_alvo="en")
                    education["field_of_study"] = traduzir_texto(education["field_of_study"], idioma_alvo="en")
                    education["degree"] = traduzir_texto(education["degree"], idioma_alvo="en")
                    
                    if "associated_title" in education:
                        education["associated_title"] = [
                        traduzir_texto(title, idioma_alvo="en") for title in education["associated_title"]
                     ]
            if "short_educations" in cv_data:
                for short in cv_data["short_educations"]:
                    short["institution"] = traduzir_texto(short["institution"], idioma_alvo="en")
                    short["field_of_study"] = traduzir_texto(short["field_of_study"], idioma_alvo="en")
                    # volun["institution"] = traduzir_texto(volun["institution"], idioma_alvo="en")
            
            if "projects" in cv_data:
                for project in cv_data["projects"]:
                    project["description"] = traduzir_texto(project["description"], idioma_alvo="en")
                    # project["institution"] = traduzir_texto(project["institution"], idioma_alvo="en")
                    project["job_title"] = traduzir_texto(project["job_title"], idioma_alvo="en")
                    # project["degree"] = traduzir_texto(project["degree"], idioma_alvo="en")
                    
                    if "associated_title" in project:
                        project["associated_title"] = [
                        traduzir_texto(title, idioma_alvo="en") for title in project["associated_title"]
                     ]
            
            if "awards" in cv_data:
                for award in cv_data["awards"]:
                    award["title"] = traduzir_texto(award["title"], idioma_alvo="en")
            
            if "languages" in cv_data:
                for language in cv_data["languages"]:
                    language["language"] = traduzir_texto(language["language"], idioma_alvo="en")
                    language["proficiency"] = traduzir_texto(language["proficiency"], idioma_alvo="en")
                    
            if "softwares" in cv_data:
                for software in cv_data["softwares"]:
                    software["software"] = traduzir_texto(software["software"], idioma_alvo="en")
                    software["proficiency"] = traduzir_texto(software["proficiency"], idioma_alvo="en")
            
            if "volunteer_work" in cv_data:
                for volun in cv_data["volunteer_work"]:
                    volun["institution"] = traduzir_texto(volun["institution"], idioma_alvo="en")
                    volun["job_name"] = traduzir_texto(volun["job_name"], idioma_alvo="en")
                    # volun["institution"] = traduzir_texto(volun["institution"], idioma_alvo="en")
                    
            if "references" in cv_data:
                for ref in cv_data["references"]:
                    ref["position"] = traduzir_texto(ref["position"], idioma_alvo="en")
                    # ref["company"] = traduzir_texto(ref["company"], idioma_alvo="en")
                    
            if "skills" in cv_data:
                for skill in cv_data["skills"]:
                    skill["skill"] = traduzir_texto(skill["skill"], idioma_alvo="en")
            
            return Response(cv_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UpdateExperience(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Recebendo os dados da requisição
            job_title = request.data.get("job_title", "")
            job_required_skills = request.data.get("jobRequiredSkills", [])

            user_role = request.data.get("role", "")
            user_skills = request.data.get("skills", [])
            
            key_words = request.data.get("keyWords", [])

            # Verificando se os dados do usuário e da vaga estão presentes
            if not key_words:
                return Response({"error": "Palavras-chave são obrigatórias"}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user_role:
                return Response({"error": "Cargo do candidato é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

            if not job_title:
                return Response({"error": "Título da vaga é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

            # Preparando o prompt para o GPT
            prompt = f"""
            Você é um especialista em Recrutamento e Seleção. Sua tarefa é gerar uma lista de tarefas e habilidades alinhadas ao cargo de "{job_title}" com base nas habilidades que o candidato já possui.

            ### Dados do Candidato:
            - Habilidades do Candidato: {', '.join(user_skills)}

            ### Requisitos da Vaga:
            - Cargo Alvo: {job_title}
            - Palavras-chave extraídas da descrição da vaga: {', '.join(key_words)}
            - Habilidades Requeridas: {', '.join(job_required_skills)}

            ### Instruções:
            - Gere de 2 a 3 frases com possíveis tarefas alinhadas ao cargo desejado.
            - Utilize **exatamente** as palavras-chave fornecidas sempre que possível, sem alterar sua forma.
            - Baseie-se apenas nas habilidades fornecidas; **não invente experiências**.
            - Seja objetivo e profissional.
            - **Responda na mesma língua em que as habilidades do candidato estão escritas.**

            ### Formato de saída:
            - Liste apenas as tarefas, **sem bullets, sem traços, sem numeração ou categorias**.
            - Cada tarefa em uma **nova linha**.
            - Nenhum título, explicação ou texto adicional antes ou depois da lista.

            Devolva **APENAS** a lista final melhorada no formato indicado.
            """

            # Chama a API OpenAI para gerar as tarefas e otimizar a descrição
            response = openai.ChatCompletion.create(
                model="gpt-4",  # Use o modelo GPT-4
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,  # Limite de tokens para evitar resposta muito longa
            )

            # Obtendo as tarefas geradas pela API
            tasks = response.choices[0].message.content

            # Retorna a resposta para o cliente
            return Response({"generatedTasks": tasks}, status=status.HTTP_200_OK)

        except Exception as e:
            # Tratando erros
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def calcular_duracao(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Calcular a diferença em dias
    diff_in_days = (end - start).days
    years = diff_in_days // 365
    months = (diff_in_days % 365) // 30
    days = (diff_in_days % 365) % 30

    return f"{years} anos, {months} meses, {days} dias"


logger = logging.getLogger(__name__)
class CartaApresentacaoView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """
        Gera carta de apresentação usando OpenAI GPT-4
        """
        try:
            # Validação do payload
            payload = self.validate_payload(request.data)
            
            # Geração do prompt otimizado
            prompt = self.generate_enhanced_prompt(payload)
            
            # Chamada à API OpenAI
            full_letter = self.generate_with_openai(prompt)
            
            # Processamento e validação da resposta
            structured_letter = self.process_ai_response(full_letter, payload['name'])
            
            # Formatação da resposta final
            return self.format_success_response(structured_letter)
            
        except ValueError as ve:
            logger.warning(f"Validation error: {str(ve)}")
            return self.format_error_response(str(ve), status.HTTP_400_BAD_REQUEST)
        except openai.error.OpenAIError as oe:
            logger.error(f"OpenAI API error: {str(oe)}")
            return self.format_error_response(
                f"Erro na geração da carta: {str(oe)}", 
                status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return self.format_error_response(
                "Erro interno no servidor",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def validate_payload(self, data):
        """Validação completa do payload recebido"""
        if not isinstance(data, dict):
            raise ValueError("O payload deve ser um objeto JSON")
        
        required_fields = ['title', 'skills', 'name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise ValueError(f"Campos obrigatórios faltando: {', '.join(missing_fields)}")
        
        valid_tone = {'formal', 'moderno', 'criativo'}
        tone = data.get('tone', 'formal')
        if tone not in valid_tone:
            raise ValueError(f"Tom inválido. Opções válidas: {', '.join(valid_tone)}")
        
        # Validação das estruturas de arrays
        for field in ['education', 'experiencia', 'estagio']:
            if field in data and not isinstance(data[field], list):
                raise ValueError(f"O campo '{field}' deve ser uma lista")
        
        return {
            'title': str(data['title']),
            'skills': str(data['skills']),
            'name': str(data['name']),
            'education': data.get('education', []),
            'experiencia': data.get('experiencia', []),
            'estagio': data.get('estagio', []),
            'tone': tone
        }

    def generate_enhanced_prompt(self, payload):
        def format_items(items, prefix=""):
            formatted = []
            for item in items:
                position = item.get('job_title', '')
                company = item.get('company', '')
                start = item.get('start_date', '')
                end = item.get('end_date', '')
                desc = item.get('description', '')
                if position and company:
                    duration = f"({start} até {end})" if start and end else ""
                    item_str = f"{prefix}{position} na {company} {duration}".strip()
                    if desc:
                        item_str += f": {desc}"
                    formatted.append(item_str)
            return "\n".join(formatted) or "Nenhuma experiência informada"

        education_str = "\n".join(
            f"{edu.get('field_of_study', '')} na {edu.get('institution', '')} (Concluído em {edu.get('end_date', '')})"
            for edu in payload['education']
            if edu.get('field_of_study') and edu.get('institution')
        ) or "Nenhuma formação informada"

        experience_str = format_items(payload['experiencia']) or "Nenhuma experiência informada"
        internship_str = format_items(payload['estagio'], "Estágio como ") or "Nenhum estágio informado"

        tone_instructions = {
            'formal': "linguagem formal e estrutura tradicional",
            'moderno': "linguagem profissional contemporânea",
            'criativo': "abordagem inovadora mantendo profissionalismo"
        }[payload['tone']]

        return f"""
        ## Instruções para Geração de Carta de Apresentação
        
        **Objetivo:** Criar uma carta de apresentação em português de Portugal com estrutura clara em 4 seções
        
        **Tom:** {tone_instructions}
        
        **Estrutura Obrigatória:**
        [SAUDAÇÃO]
        (linha única com saudação formal, ex.: Exmo. Senhor Director / Gestor de Recursos Humanos)

        [INTRODUÇÃO]
        (1 parágrafo contínuo com:)
        - Apresentação breve (nome, formação)
        - Objetivo profissional
        - Motivação para a vaga específica

        [DESENVOLVIMENTO]
        (3-4 parágrafos:)
        - Experiência profissional detalhada, listando cargos e responsabilidades com bullets
        - Habilidades adquiridas
        - Conexão com a vaga alvo

        [CONCLUSÃO]
        (1 parágrafo contínuo com:)
        - Disponibilidade para entrevista
        - Agradecimento
        - Fechamento cortês

        [ASSINATURA]
        (linha única com o nome completo)

        **Dados do Candidato:**
        - Nome: {payload['name']}
        - Formação: {education_str}
        - Experiência profissional: {experience_str}
        - Estágios: 
        {internship_str}

        **Dados da Vaga:**
        - Cargo: {payload['title']}
        - Habilidades requeridas: {payload['skills']}

        **Regras Estritas:**
        1. Todas as seções devem ser preenchidas
        2. Use os marcadores [SEÇÃO] exatamente como definidos, mas o texto final deve ser fluido sem quebras de linha internas
        3. Limite de 400-500 palavras
        4. Destaque 2-3 competências-chave
        5. Use palavras-chave da descrição da vaga
        6. Evite clichês como 'sou proativo'
        7. Seja específico sobre conquistas
        8. Mantenha coerência com o tom {payload['tone']}
        """

    def generate_with_openai(self, prompt):
        """Integração com a API da OpenAI"""
        # openai.api_key = settings.OPENAI_API_KEY
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um especialista em RH com 15 anos de experiência em redação de cartas de apresentação profissionais."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1200,
            top_p=0.9,
            frequency_penalty=0.2,
            presence_penalty=0.1
        )
        
        return response.choices[0].message.content

    
    def process_ai_response(self, text, candidate_name):
        """Processa e valida a resposta da IA"""
        # Remove múltiplas quebras de linha e espaços excessivos
        text = re.sub(r'\n{2,}', '\n', text.strip())
        text = re.sub(r'\s+', ' ', text)  # Substitui múltiplos espaços por um único espaço

        # Padrões de regex melhorados para capturar o conteúdo sem marcadores
        section_patterns = {
            "saudacao": r"\[SAUDAÇÃO\](.*?)(?=\[INTRODUÇÃO\]|\Z)",
            "introducao": r"\[INTRODUÇÃO\](.*?)(?=\[DESENVOLVIMENTO\]|\Z)",
            "desenvolvimento": r"\[DESENVOLVIMENTO\](.*?)(?=\[CONCLUSÃO\]|\Z)",
            "conclusao": r"\[CONCLUSÃO\](.*?)(?=\[ASSINATURA\]|\Z)",
            "assinatura": r"\[ASSINATURA\](.*)"
        }
        
        sections = {}
        for section, pattern in section_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            content = match.group(1).strip() if match and match.group(1) else ""
            sections[section] = self.clean_section(content)

        # Garante os elementos críticos
        if not sections["saudacao"]:
            sections["saudacao"] = "Exmo. Senhor Director / Gestor de Recursos Humanos"
        if not sections["assinatura"]:
            sections["assinatura"] = candidate_name

        # Valida conteúdo mínimo e remove quebras de linha internas indesejadas
        for section in ["introducao", "desenvolvimento", "conclusao"]:
            if sections[section]:
                sections[section] = re.sub(r'\n', ' ', sections[section])  # Remove quebras de linha internas
                if len(sections[section].split()) < 15:  # Pelo menos 15 palavras
                    logger.warning(f"Seção {section} muito curta: {sections[section]}")

        return sections
    

    def clean_section(self, text):
        """Limpa o texto da seção removendo marcadores e espaços extras"""
        text = re.sub(r'^\[.*\]\s*', '', text.strip())  # Remove marcadores no início
        text = re.sub(r'\s+', ' ', text)  # Normaliza espaços
        return text

    def format_success_response(self, sections):
        """Formata a resposta de sucesso"""
        full_text = "\n\n".join([
            sections["saudacao"],
            sections["introducao"],
            sections["desenvolvimento"],
            sections["conclusao"],
            sections["assinatura"]
        ])
        
        word_count = sum(len(section.split()) for section in sections.values())
        
        return Response({
            "success": True,
            "letter": {
                "full_text": full_text,
                "sections": {
                    "saudacao": sections["saudacao"],
                    "introducao": sections["introducao"],
                    "desenvolvimento": sections["desenvolvimento"],
                    "conclusao": sections["conclusao"],
                    "assinatura": sections["assinatura"]
                }
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": "gpt-4",
                "word_count": word_count,
                "section_word_counts": {
                    section: len(text.split())
                    for section, text in sections.items()
                }
            }
        }, status=status.HTTP_200_OK)

    def format_error_response(self, message, status_code):
        """Formata a resposta de erro"""
        return Response({
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }, status=status_code)
            
class MpesaPayments(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone_number = request.data.get("phone_number")
        amount = request.data.get("amount")
        transaction_reference = request.data.get("reference")

        if not phone_number or not amount:
            return Response(
                {"error": "O telefone e o valor são obrigatórios!"}, status=400
            )

        api_context = APIContext()
        api_context.api_key = settings.MPESA_API_KEY
        api_context.public_key = settings.MPESA_PUBLIC_KEY
        api_context.ssl = True
        api_context.method_type = APIMethodType.POST
        api_context.address = settings.MPESA_URL
        api_context.port = 18352
        api_context.path = "/ipg/v1x/c2bPayment/singleStage/"

        api_context.add_header("Origin", "*")
        api_context.add_parameter("input_TransactionReference", transaction_reference)
        api_context.add_parameter("input_CustomerMSISDN", phone_number)
        api_context.add_parameter("input_Amount", amount)
        api_context.add_parameter("input_ThirdPartyReference", "MetroJobs")
        api_context.add_parameter(
            "input_ServiceProviderCode", settings.MPESA_SERVICE_PROVIDER_CODE
        )

        try:
            api_request = APIRequest(api_context)
            result = api_request.execute()
            
            pprint(result.status_code)
            pprint(result.headers)
            pprint(result.body)

            return Response(
                {"status": result.status_code, "response": result.body}, status=200
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,  # 'live' para produção
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)

class GenerateClientTokenView(APIView):
    permission_classes = [IsAuthenticated]  
    def get(self, request):
        """Gera o clientToken para o frontend"""
        try:
            # Geração do token
            client_token = braintree.ClientToken.generate()
            return JsonResponse({"client_token": client_token})
        except braintree.exceptions.braintree_error.BraintreeError as e:
            return JsonResponse({"error": str(e)}, status=500)


class PayPalCardPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('orderID')

        # Obter access token
        auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET)
        token_res = requests.post(
            'https://api-m.paypal.com/v1/oauth2/token',
            headers={'Accept': 'application/json'},
            data={'grant_type': 'client_credentials'},
            auth=auth
        )
        access_token = token_res.json().get('access_token')

        if not access_token:
            return Response({'error': 'Token não obtido'}, status=400)

        # Capturar pagamento
        capture_res = requests.post(
            f'https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
        )

        return Response(capture_res.json())

#