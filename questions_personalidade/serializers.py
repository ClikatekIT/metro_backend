from rest_framework import serializers
from .models import QuestionPersonalidade, AnswerPersonalidade, Test

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionPersonalidade
        fields = '__all__'

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = '__all__'

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerPersonalidade
        fields = '__all__'
