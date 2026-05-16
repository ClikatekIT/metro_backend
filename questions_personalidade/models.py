from django.db import models
from curriculum.models import User  # Importe o modelo User do aplicativo curriculum

class QuestionPersonalidade(models.Model):
    text = models.TextField()
    options = models.JSONField()

    def __str__(self):
        return self.text


class Test(models.Model):
    user = models.ForeignKey(
        User,  # Relaciona o Test com o modelo User
        on_delete=models.CASCADE,  # Define o comportamento ao excluir o usuário
        related_name="tests"  # Nome para acessar os testes de um usuário (ex: user.tests.all())
    )
    created_at = models.DateTimeField(auto_now_add=True)
    classificacao = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Teste de {self.user.name} - Criado em {self.created_at}"
    
class AnswerPersonalidade(models.Model):
    question = models.ForeignKey(
        "QuestionPersonalidade",  # Relaciona a resposta com a pergunta
        on_delete=models.CASCADE,
        related_name="answers"  # Nome para acessar as respostas de uma pergunta (ex: question.answers.all())
    )
    user = models.ForeignKey(
        User,  # Relaciona a resposta com o usuário
        on_delete=models.CASCADE,  # Define o comportamento ao excluir o usuário
        related_name="personalidade_answers"  # Nome para acessar as respostas de um usuário (ex: user.personalidade_answers.all())
    )
    answer = models.TextField()  # Resposta fornecida pelo usuário
    test = models.ForeignKey(
        "Test",  # Relaciona a resposta com o teste
        on_delete=models.CASCADE,
        related_name="personalidade_answers"  # Nome para acessar as respostas de um teste (ex: test.personalidade_answers.all())
    )

    def __str__(self):
        return f"Resposta de {self.user.name} à pergunta '{self.question.text}'"

class PersonalityScore(models.Model):
    test = models.OneToOneField(Test, on_delete=models.CASCADE, related_name='personality_score')
    extroversao = models.IntegerField()
    amabilidade = models.IntegerField()
    consciencia = models.IntegerField()
    neuroticismo = models.IntegerField()
    abertura_experiencia = models.IntegerField()

    def __str__(self):
        return f"Scores for Test ID: {self.test.id}"