from django.db import models
from questions_personalidade.models import Test 
from curriculum.models import User  # Importa o modelo User correto


class CognitiveTest(models.Model):
    summary = models.TextField()
    skills = models.JSONField()
    test_type = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    id_teste_personalidade = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='cognitive_tests')  # Chave estrangeira
       # Novos campos para cargo atual e desejado
    cargo_atual = models.CharField(max_length=255, blank=True, null=True)
    cargo_desejado = models.CharField(max_length=255, blank=True, null=True)

class Question(models.Model):
    test = models.ForeignKey(CognitiveTest, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    options = models.JSONField()  
    metadata = models.JSONField(null=True, blank=True)  
    correct_answer = models.CharField(max_length=255)  


class Feedback(models.Model):
    cognitive_test = models.ForeignKey(CognitiveTest, on_delete=models.CASCADE, related_name='feedbacks')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Opcional, para associar ao usuário
    feedback_data = models.JSONField()  # Armazena o feedback estruturado (JSON)
    created_at = models.DateTimeField(auto_now_add=True)
    # user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created_at']

class UserAnswer(models.Model):
    feedback = models.ForeignKey(Feedback, related_name='user_answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='user_answers', on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)