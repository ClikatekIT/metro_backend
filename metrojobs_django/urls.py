from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenBlacklistView,
)
from curriculum.views import EmailTokenObtainPairView, GoogleTokenObtainPairView
from entrevistas import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('curriculum.urls')),  # URLs do app 'curriculum'
    path('api/interview/', views.InterviewAPIView.as_view()),
    path('api/interview/<int:interview_id>/question/<int:question_id>/', views.AnswerQuestionAPIView.as_view(), name='answer_question'),
    path('api/', include('questions_personalidade.urls')),
    path('', include('carrier_guide.urls')),  
    path('api/interview/<int:interview_id>/update_rating/', views.UpdateInterviewRating.as_view(), name="update_interview_rating"),
    path('api/getInterviews/', views.InterviewListView.as_view()),
    path('api/deleteInterview/<int:interview_id>/', views.DeleteInterviewView.as_view(), name='delete-interview'),
    # URLs para autenticação com JWT
    path('api/getInterviewCount/', views.UserInterviewCountView.as_view(), name='get-interview-count'),
    path('api/token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/google/', GoogleTokenObtainPairView.as_view(), name='google-login'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('api/analyze-cv/', views.CVAnalysisAPIView.as_view(), name='analyze_cv'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
