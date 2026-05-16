from django.db import models
from curriculum.models import User  # Importa o modelo User correto

class Company(models.Model):
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255)

class Position(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    job_description = models.TextField()


class Interview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Campo final
    position = models.ForeignKey('Position', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    classificacao = models.IntegerField(null=True, blank=True)
    empresa = models.CharField(max_length=255)

class Question(models.Model):
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE)
    text = models.TextField()
    audio_path = models.CharField(max_length=255, blank=True, null=True)

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    feedback = models.TextField(null=True, blank=True)