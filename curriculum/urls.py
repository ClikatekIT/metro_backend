from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    MpesaPayments,
    JobDescriptionViewSet,
    GenerateKeyWordsView,
    UpdateExperience,
    CartaApresentacaoView,
    CVViewSet,
    GenerateClientTokenView,
    PersonalInfoViweSet,
    CheckEmailExistsView,
    UserLoggedInView,
    CreditViewSet,
    UsoCreditoViewSet,
    TransacaoViewSet,
    GenerateTasksView,
    TraduzirCV,
    PayPalCardPaymentView,
    get_csrf_token,
)

# Criação do router
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"personal-info", PersonalInfoViweSet, basename="personalinfo")
router.register(r"cvs", CVViewSet, basename="cv")
router.register(r"job-descriptions", JobDescriptionViewSet, basename="job-description")
router.register(r'credit', CreditViewSet, basename='credit')
router.register(r'uso_credito', UsoCreditoViewSet, basename='uso_credito')
router.register(r'transacoes', TransacaoViewSet, basename='transacoes')
router.register(
    r"generate-cover-letter", CartaApresentacaoView, basename="generate-cover-letter"
)

urlpatterns = router.urls

# Adicionando a rota para retornar o usuário logado
urlpatterns += [
    path("user/logged-in/", UserLoggedInView.as_view(), name="user_logged_in"),
    path("mpesa/create-payment/", MpesaPayments.as_view(), name="mpesa_create_payment"),
    path(
        "paypal/card-payment/",
        PayPalCardPaymentView.as_view(),
        name="paypal_card_payment",
    ),
    path("adjust-resume/", UpdateExperience.as_view(), name="adjust-resume"),
    path("open-ai/generate-tasks/", GenerateTasksView.as_view(), name="generate_tasks"),
    path("keywords/", GenerateKeyWordsView.as_view(), name="keywords"),
    path('traduzir-cv/', TraduzirCV.as_view(), name='traduzir-cv'),
    path('get-csrf-token/', get_csrf_token),
    path("generate_token/", GenerateClientTokenView.as_view(), name="generate_token"),
    path('check-email/', CheckEmailExistsView.as_view(), name='check-email'),
]
