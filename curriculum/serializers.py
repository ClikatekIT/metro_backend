from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed,  PermissionDenied
from django.contrib.auth import authenticate
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from .models import (
    User,
    Factura,
    Education,
    ShortEducation,
    Experience,
    ExecutableProject,
    Internship,
    Volunteer,
    Award,
    PersonalInfo,
    Skill,
    Language,
    Software,
    Referenc,
    CV,
    TipoTransacao,
    Transacao,
    Credit,
    ExperienceJD,
    EducationJD,
    JobDescription,
    LanguageJD,
    SoftwareJD,
)


class BaseRestrictedSerializer(serializers.ModelSerializer):
    """Base serializer para restringir acesso a dados apenas para administradores."""

    def get_queryset(self):
        request = self.context.get("request")
        queryset = super().get_queryset()
        if request and not request.user.is_staff:
            return queryset.filter(user=request.user)
        return queryset

    def validate(self, data):
        request = self.context.get("request")
        if (
            not request.user.is_staff
            and "user" in data
            and data["user"] != request.user
        ):
            raise PermissionDenied(
                "Você não tem permissão para modificar dados de outros usuários."
            )
        return data


# Serializer para o modelo User
class UserSerializer(BaseRestrictedSerializer):
    ultimo_credito = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "password",
            "is_active",
            "is_staff",
            "status",
            "credito",
            "ultimo_credito",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"password": {"write_only": True}}
        read_only_fields = ["created_at", "updated_at"]
        
    def get_ultimo_credito(self, obj):
        ultimo_credito = Credit.objects.filter(user=obj).order_by("-created_at").first()
        return ultimo_credito.valid_until if ultimo_credito else None

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User.objects.create_user(password=password, **validated_data)
        return user


class EducationSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Education
        fields = "__all__"


class ShortEducationSerializer(BaseRestrictedSerializer):
    class Meta:
        model = ShortEducation
        fields = "__all__"


class ExperienceSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Experience
        fields = "__all__"


class ExecutableProjectSerializer(BaseRestrictedSerializer):
    class Meta:
        model = ExecutableProject
        fields = "__all__"


class InternshipSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Internship
        fields = "__all__"


class VolunteerSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Volunteer
        fields = "__all__"


class AwardSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Award
        fields = "__all__"


class PersonalInfoSerializer(BaseRestrictedSerializer):
    class Meta:
        model = PersonalInfo
        fields = "__all__"


class SkillSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class LanguageSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Language
        fields = "__all__"


class SoftwareSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Software
        fields = "__all__"


class ReferencSerializer(BaseRestrictedSerializer):
    class Meta:
        model = Referenc
        fields = "__all__"


def update_related_objects(model, instance, related_manager, related_data):
    """
    Atualiza objetos relacionados de forma eficiente e segura
    """
    if related_data is None:
        return  # Se não houver dados, não faz nada

    with transaction.atomic():
        existing_objects = {obj.id: obj for obj in related_manager.all()}
        updated_ids = set()
        new_objects = []

        for data in related_data:
            obj_id = data.get("id")
            if obj_id and obj_id in existing_objects:
                # Atualização de objeto existente
                obj = existing_objects[obj_id]
                for attr, value in data.items():
                    if attr != 'id' and hasattr(obj, attr):
                        setattr(obj, attr, value)
                obj.save()
                updated_ids.add(obj_id)
            else:
                # Criação de novo objeto
                new_obj = model.objects.create(**data)
                new_objects.append(new_obj)

        # Remove objetos não incluídos nos dados atualizados
        to_remove = set(existing_objects.keys()) - updated_ids
        if to_remove:
            related_manager.filter(id__in=to_remove).delete()

        # Adiciona os novos objetos à relação
        if new_objects:
            related_manager.add(*new_objects)


class CVSerializer(BaseRestrictedSerializer):
    educations = EducationSerializer(many=True)
    short_educations = ShortEducationSerializer(many=True)
    experiences = ExperienceSerializer(many=True)
    projects = ExecutableProjectSerializer(many=True)
    internships = InternshipSerializer(many=True)
    volunteer_work = VolunteerSerializer(many=True)
    awards = AwardSerializer(many=True)
    skills = SkillSerializer(many=True)
    languages = LanguageSerializer(many=True)
    softwares = SoftwareSerializer(many=True)
    references = ReferencSerializer(many=True)
    personal_info = PersonalInfoSerializer(required=False, allow_null=True)
    class Meta:
        model = CV
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            personal_info = instance.personal_info
        except PersonalInfo.DoesNotExist:
            personal_info = None
        representation["personal_info"] = PersonalInfoSerializer(personal_info).data if personal_info else None
        return representation


    @transaction.atomic
    def create(self, validated_data):
        related_data = {}
        related_models = {
            'educations': Education,
            'short_educations': ShortEducation,
            'experiences': Experience,
            'projects': ExecutableProject,
            'internships': Internship,
            'volunteer_work': Volunteer,
            'awards': Award,
            'skills': Skill,
            'languages': Language,
            'softwares': Software,
            'references': Referenc,
            # 'personal_info': PersonalInfo
        }

    # Extrai os dados de relacionamento
        for field in related_models.keys():
            related_data[field] = validated_data.pop(field, [])
        
        personal_info_data = validated_data.pop('personal_info', None)

    # Cria o CV apenas com os campos não-relacionais
        cv = CV.objects.create(**validated_data)

    # Cria e associa os objetos relacionados
        for field, model_class in related_models.items():
            objects = [model_class.objects.create(**data) for data in related_data[field]]
            getattr(cv, field).set(objects)
            
        if personal_info_data:
            PersonalInfo.objects.create(cv=cv, **personal_info_data)

        return cv

    @transaction.atomic
    def update(self, instance, validated_data):
        for field in ['description', 'language_cv', 'analise_percent', 'job_description_percent']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()

    # Atualiza ou cria o personal_info vinculado ao CV
        if 'personal_info' in validated_data:
            personal_info_data = validated_data.pop('personal_info')
            PersonalInfo.objects.update_or_create(
                cv=instance,
                defaults=personal_info_data
        )
            instance.refresh_from_db()

        related_fields = {
            'educations': (Education, instance.educations),
            'short_educations': (ShortEducation, instance.short_educations),
            'experiences': (Experience, instance.experiences),
            'projects': (ExecutableProject, instance.projects),
            'internships': (Internship, instance.internships),
            'volunteer_work': (Volunteer, instance.volunteer_work),
            'awards': (Award, instance.awards),
            'skills': (Skill, instance.skills),
            'languages': (Language, instance.languages),
            'softwares': (Software, instance.softwares),
            'references': (Referenc, instance.references)
        }

        for field, (model_class, manager) in related_fields.items():
            if field in validated_data:
                update_related_objects(
                    model_class,
                    instance,
                    manager,
                    validated_data[field]
                )

        return instance



# serializers.py
class CreditSerializer(serializers.ModelSerializer):
    numero_factura = serializers.SerializerMethodField()
    referencia_pagamento = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = [
            "id",
            "user",
            "metodo_pagamento",
            "valor",
            "valor_convertido",
            "created_at",
            "updated_at",
            "valid_until",
            "numero_factura",
            "referencia_pagamento",
        ]

    def get_numero_factura(self, obj):
        return obj.factura.numero if hasattr(obj, 'factura') else None

    def get_referencia_pagamento(self, obj):
        return obj.transacao.referencia if hasattr(obj, 'transacao') else None

    def create(self, validated_data):
        with transaction.atomic():
            referencia = validated_data.pop('reference', None)
            user = validated_data["user"]
            valor_pago_mzn = validated_data["valor"]
            agora = timezone.now()

            # Definir taxa baseada no valor
            if valor_pago_mzn >= Decimal("850.00"):
                taxa_conversao = Decimal("24.29")  # com desconto
            else:
                taxa_conversao = Decimal("25.00")  # padrão

            # Definir validade
            ultimo_credito = Credit.objects.filter(user=user).order_by("-valid_until").first()
            if not ultimo_credito or ultimo_credito.valid_until < agora:
                valid_until = agora + timedelta(days=30)
            else:
                nova_validade = ultimo_credito.valid_until + timedelta(days=30)
                limite_maximo = agora + timedelta(days=90)
                valid_until = min(nova_validade, limite_maximo)

            # Criar crédito
            credito = super().create(validated_data)
            credito.valid_until = valid_until

            # Calcular e definir valor convertido
            credito.valor_convertido = valor_pago_mzn / taxa_conversao
            credito.save()

            # Criar transação
            transacao = Transacao.objects.create(
                user=credito.user,
                tipo=TipoTransacao.objects.get(nome="Compra de crédito"),
                valor=valor_pago_mzn,
                referencia=referencia,
                credit=credito
            )

            # Criar fatura
            Factura.objects.create(
                user=credito.user,
                credit=credito,
                valor=valor_pago_mzn,
                metodo_pagamento=credito.metodo_pagamento,
                referencia_pagamento=transacao.referencia
            )

            # Atualizar saldo do usuário
            user.credito += credito.valor_convertido
            user.save()

            return credito



class UsoCreditoSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    valor_creditos = serializers.DecimalField(max_digits=10, decimal_places=2)
    referencia = serializers.CharField(max_length=100)

    def _expirar_creditos_vencidos(self, user):
        vencidos = Credit.objects.filter(
            user=user,
            valid_until__lt=timezone.now(),
            valor_convertido__gt=0
        )

        for credito in vencidos:
            user.credito = max(user.credito - credito.valor_convertido, 0)
            user.save()
            credito.valor_convertido = 0
            credito.save()

    def create(self, validated_data):
        with transaction.atomic():
            user = validated_data["user"]
            valor_creditos = validated_data["valor_creditos"]
            referencia = validated_data["referencia"]

            # Expirar créditos vencidos antes de usar
            self._expirar_creditos_vencidos(user)

            taxa_conversao = Decimal("25.00")  # valor unitário padrão no uso
            valor_mzn = valor_creditos * taxa_conversao

            tipo_transacao = TipoTransacao.objects.get(nome="Uso de crédito")
            transacao = Transacao.objects.create(
                user=user,
                tipo=tipo_transacao,
                valor=valor_mzn,
                referencia=referencia,
            )

            user.credito -= valor_creditos
            user.save()
            
            if user.credito <= 0:
                Credit.objects.filter(user=user, valor_convertido=0).update(valid_until=None)

            return transacao


class TipoTransacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoTransacao
        fields = "__all__"

    @staticmethod
    def create_default_types():
        """Cria os tipos de transação padrão se não existirem."""
        tipos_default = ['Uso de crédito', 'Compra de crédito', 'Reversão']

        for tipo_nome in tipos_default:
            # Garantir que cada tipo de transação exista
            TipoTransacao.objects.get_or_create(nome=tipo_nome)

    def create(self, validated_data):
        self.create_default_types()

        tipo_transacao = super().create(validated_data)
        return tipo_transacao


class TransacaoSerializer(BaseRestrictedSerializer):
    tipo = TipoTransacaoSerializer(read_only=True)
    numero_factura = serializers.SerializerMethodField()

    class Meta:
        model = Transacao
        fields = "__all__"
        
    def get_numero_factura(self, obj):
        # Verifica se existe Credit → Factura vinculada
        if hasattr(obj, "credit") and obj.credit and hasattr(obj.credit, "factura"):
            return obj.credit.factura.numero
        return None


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador para autenticação via e-mail, incluindo dados extras no token.
    """

    def validate(self, attrs):
        email = attrs.get("email") or attrs.get("username")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"), email=email, password=password
        )

        if not user:
            try:
                user = User.objects.get(email=email)
                if not user.check_password(password):
                    raise AuthenticationFailed("Credenciais inválidas.")
                if not user.is_active:
                    raise AuthenticationFailed("Usuário inativo.")
            except User.DoesNotExist:
                raise AuthenticationFailed("Usuário não encontrado.")

        refresh = self.get_token(user)

        # Retornar os tokens e dados extras, convertendo Decimal para float
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
        }

    @classmethod
    def get_token(cls, user):
        """
        Personaliza o payload do token para incluir informações extras.
        """
        token = super().get_token(user)
        token["id"] = str(user.id)
        token["email"] = user.email
        token["name"] = user.name
        token["is_staff"] = user.is_staff  # Adicionando is_staff ao payload
        return token


class UserDetailSerializer(serializers.ModelSerializer):
    educations = EducationSerializer(many=True, read_only=True)
    short_educations = ShortEducationSerializer(many=True, read_only=True)
    experiences = ExperienceSerializer(many=True, read_only=True)
    projects = ExecutableProjectSerializer(many=True, read_only=True)
    internships = InternshipSerializer(many=True, read_only=True)
    volunteer_work = VolunteerSerializer(many=True, read_only=True)
    awards = AwardSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    softwares = SoftwareSerializer(many=True, read_only=True)
    references = ReferencSerializer(many=True, read_only=True)
    cvs = CVSerializer(many=True, read_only=True)
    transacoes = TransacaoSerializer(many=True, read_only=True)
    credit = CreditSerializer(many=True, read_only=True)
    personal_info = PersonalInfoSerializer(many=True, read_only=True)

    class Meta:
        fields = "__all__"


class ExperienceJDSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperienceJD
        fields = "__all__"


class EducationJDSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationJD
        fields = "__all__"


class LanguageJDSerializer(serializers.ModelSerializer):
    class Meta:
        model = LanguageJD
        fields = "__all__"


class SoftwareJDSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareJD
        fields = "__all__"


class JobDescriptionSerializer(serializers.ModelSerializer):
    experience = ExperienceJDSerializer(many=True)
    education = EducationJDSerializer(many=True)
    language = LanguageJDSerializer(many=True)
    software = SoftwareJDSerializer(many=True)

    class Meta:
        model = JobDescription
        fields = "__all__"

    def create(self, validated_data):
        experiences_data = validated_data.pop("experience", [])
        educations_data = validated_data.pop("education", [])
        languages_data = validated_data.pop("language", [])
        softwares_data = validated_data.pop("software", [])

        # Criar a instância principal
        job_description = JobDescription.objects.create(**validated_data)
        job_description.save()  # Salvar antes de relacionar os objetos ManyToMany

        # Criar e associar experiências
        experiences = [ExperienceJD.objects.create(**data) for data in experiences_data]
        job_description.experience.set(experiences)

        # Criar e associar educações
        educations = [EducationJD.objects.create(**data) for data in educations_data]
        job_description.education.set(educations)

        # Criar e associar línguas
        languages = [LanguageJD.objects.create(**data) for data in languages_data]
        job_description.language.set(languages)

        # Criar e associar softwares
        softwares = [SoftwareJD.objects.create(**data) for data in softwares_data]
        job_description.software.set(softwares)

        return job_description

    def update(self, instance, validated_data):
        experiences_data = validated_data.pop("experience", [])
        educations_data = validated_data.pop("education", [])
        languages_data = validated_data.pop("language", [])
        softwares_data = validated_data.pop("software", [])

        # Atualizar campos simples
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        # Atualizar experiências
        if experiences_data:
            experiences = [
                ExperienceJD.objects.create(**data) for data in experiences_data
            ]
            instance.experience.set(experiences)

        # Atualizar educações
        if educations_data:
            educations = [
                EducationJD.objects.create(**data) for data in educations_data
            ]
            instance.education.set(educations)

        # Atualizar línguas
        if languages_data:
            languages = [LanguageJD.objects.create(**data) for data in languages_data]
            instance.language.set(languages)

        # Atualizar softwares
        if softwares_data:
            softwares = [SoftwareJD.objects.create(**data) for data in softwares_data]
            instance.software.set(softwares)

        return instance
