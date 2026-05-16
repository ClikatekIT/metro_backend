from django.urls import path
from .views import generate_cognitive_test, fetch_cognitive_test, feedback_teste, fetch_user_feedbacks, check_personality_test

urlpatterns = [
    path('api/cognitive-test/', generate_cognitive_test, name='generate_cognitive_test'),
    path('api/fetch_cognitive_test/', fetch_cognitive_test, name='fetch_cognitive_test'),
    path('api/feedback-teste/', feedback_teste, name='feedback_teste'),
    path('api/user-feedbacks/', fetch_user_feedbacks, name='fetch_user_feedbacks'),
    path('api/check-personality-test/', check_personality_test, name='check_personality_test'),
]