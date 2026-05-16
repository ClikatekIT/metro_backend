from rest_framework import serializers
from .models import Interview, Question, Answer, Position
from curriculum.models import User  # Importa o modelo User correto
from django.conf import settings

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'title']  # Inclui o ID e o título da posição

class InterviewSerializer(serializers.ModelSerializer):
    position = PositionSerializer(read_only=True)  # Inclui os dados da posição relacionada

    class Meta:
        model = Interview
        fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'text', 'audio_path', 'audio_url']

    def get_audio_url(self, obj):
        if obj.audio_path:
            return f"{settings.MEDIA_URL}{obj.audio_path}"
        return None

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'