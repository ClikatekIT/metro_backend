from django.urls import path
from .views import QuestionListView, SaveAnswerView 

urlpatterns = [
    path('questions/', QuestionListView.as_view(), name='question-list'),
    path('answers/', SaveAnswerView.as_view(), name='save-answer'),
    # path('personality-scores/', PersonalityScoreView.as_view(), name='personality-scores'),

]

