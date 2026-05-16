from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
import uuid
import base64
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField 
from datetime import timedelta
from django.utils import timezone


class UserManager(BaseUserManager):
    """Gerenciador de usuários customizado."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("O e-mail é obrigatório")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)  # Criptografa a senha
            user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Cria um superusuário com permissões de administrador"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superusuário precisa ter is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusuário precisa ter is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Modelo de usuário customizado"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default="Ativo")
    credito = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()  # Usa o gerenciador de usuários customizado

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    def __str__(self):
        return self.email

class TipoUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    users = models.ManyToManyField(User, related_name="tipos", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def assign_default_user_type(sender, instance, created, **kwargs):
    if created:
        default_type, _ = TipoUser.objects.get_or_create(
            slug="normal", defaults={"name": "Normal"}
        )
        instance.tipos.add(default_type)


# Função para criar tipos padrão
def create_default_user_types():
    TipoUser.objects.get_or_create(slug="normal", defaults={"name": "Normal"})
    TipoUser.objects.get_or_create(slug="admin", defaults={"name": "Admin"})


# Modelo para Educação
class Education(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations")
    institution = models.CharField(max_length=200)
    degree = models.CharField(max_length=100)
    field_of_study = models.CharField(max_length=100, null=True, blank=True)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.degree} at {self.institution}"


# Modelo para Educação Reduzida (Short Education)
class ShortEducation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="short_educations"
    )
    institution = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Short education at {self.institution}"


# Modelo para Experiências
class Experience(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="experiences")
    job_title = models.CharField(max_length=100)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    company = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField()
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_title} at {self.company}"


# Modelo para Projetos Executáveis
class ExecutableProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    job_title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    project_name = models.CharField(max_length=150)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.project_name


# Modelo para Estágio
class Internship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="internships")
    job_title = models.CharField(max_length=100)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    company = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Internship as {self.job_title} at {self.company}"


# Modelo para Voluntariado
class Volunteer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="volunteer_work"
    )
    institution = models.CharField(max_length=200)
    job_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Volunteer at {self.institution}"


# Modelo para Prêmios
class Award(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="awards")
    title = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# Modelo para Informações Pessoais
class PersonalInfo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.OneToOneField(
        "CV", on_delete=models.CASCADE, related_name="personal_info", blank=True, null=True)
    phone = models.CharField(max_length=20)
    birth_date = models.DateField()
    name= models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField()
    gender = models.CharField(max_length=10, default="")
    photo = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Personal Info for {self.cv.description}"

    def image_to_base64(self):
        if self.photo:
            return self.photo
        return None

    def save_base64_image(self, base64_data):
        format, imgstr = base64_data.split(";base64,")
        ext = format.split("/")[-1]
        image_data = ContentFile(
            base64.b64decode(imgstr), name=f"{self.cv.user.id}_photo.{ext}"
        )
        self.photo = base64_data


# Modelo para Habilidades
class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skills")
    skill = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.skill


# Modelo para Linguagens
class Language(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="languages")
    language = models.CharField(max_length=50)
    proficiency = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.language} ({self.proficiency})"


# Modelo para Softwares
class Software(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="softwares")
    software = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.software} ({self.proficiency})"


# Modelo para Referências (Renomeado para Referenc)
class Referenc(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referenc")
    name = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    email = models.EmailField()
    contact = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Referenc: {self.name} at {self.company}"


class CV(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cvs")
    description = models.CharField(max_length=100)
    language_cv = models.CharField(max_length=100, blank=True)
    job_description_percent= models.DecimalField(max_digits=5, decimal_places=2, null=True)
    analise_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    educations = models.ManyToManyField(Education, related_name="cvs")
    short_educations = models.ManyToManyField(ShortEducation, related_name="cvs")
    experiences = models.ManyToManyField(Experience, related_name="cvs")
    projects = models.ManyToManyField(ExecutableProject, related_name="cvs")
    internships = models.ManyToManyField(Internship, related_name="cvs")
    volunteer_work = models.ManyToManyField(Volunteer, related_name="cvs")
    awards = models.ManyToManyField(Award, related_name="cvs")
    skills = models.ManyToManyField(Skill, related_name="cvs")
    languages = models.ManyToManyField(Language, related_name="cvs")
    softwares = models.ManyToManyField(Software, related_name="cvs")
    references = models.ManyToManyField(Referenc, related_name="cvs")
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description


# Modelo para Tipo de Transação
class TipoTransacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


class Credit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="credit")
    metodo_pagamento = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)  # Valor em MZN
    valor_convertido = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Créditos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    valid_until = models.DateTimeField(null=True)

    def save(self, *args, **kwargs):
        if not self.valid_until:
            self.valid_until = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

class Factura(models.Model):
    numero = models.CharField(max_length=20, unique=True)  # FAC-YYYYMMDD-XXXX
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    credit = models.OneToOneField('Credit', on_delete=models.CASCADE, related_name='factura')
    data_emissao = models.DateTimeField(auto_now_add=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=50)
    referencia_pagamento = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-data_emissao']

    def save(self, *args, **kwargs):
        if not self.numero:
            # Busca a última factura do dia
            hoje = timezone.now().date()
            ultima_factura = Factura.objects.filter(
                data_emissao__date=hoje
            ).order_by('-id').first()
            
            # Determina o próximo número sequencial
            sequencial = 1
            if ultima_factura:
                try:
                    ultimo_numero = int(ultima_factura.numero.split('-')[-1])
                    sequencial = ultimo_numero + 1
                except (IndexError, ValueError):
                    pass
            
            # Formata o número
            self.numero = f"FAC-{timezone.now().strftime('%Y%m%d')}-{str(sequencial).zfill(4)}"
        super().save(*args, **kwargs)
class Transacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transacoes")
    tipo = models.ForeignKey(TipoTransacao, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    credit = models.OneToOneField('Credit', on_delete=models.SET_NULL, null=True, blank=True, related_name='transacao')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tipo} - {self.valor}"

    
class ExperienceJD(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_title = models.CharField(max_length=100)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    year_of_experience = models.CharField(max_length=20, null=True)
    job_skills = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.job_title
    
class EducationJD(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    field_of_study = models.CharField(max_length=100, null=True, blank=True)
    associated_title = ArrayField(models.CharField(max_length=100), blank=True, default=list)
    degree = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True) 

    def __str__(self):
        return self.field_of_study
    
class LanguageJD(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    language = models.CharField(max_length=50)
    proficiency = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.language} ({self.proficiency})"


# Modelo para Softwares
class SoftwareJD(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    software = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)  # Campo para data de criação
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.software} ({self.proficiency})"
    
class JobDescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    description = models.TextField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_descriptions')
    experience = models.ManyToManyField(ExperienceJD, related_name='job_descriptions')
    education = models.ManyToManyField(EducationJD, related_name='job_descriptions')
    language = models.ManyToManyField(LanguageJD, related_name='job_descriptions')
    software = models.ManyToManyField(SoftwareJD, related_name='job_descriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Job Description {self.id} - {self.description[:50]}...'