from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from curriculum.models import Credit, User  # Ajuste o import para o seu app
from django.db import transaction
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Expira créditos vencidos e atualiza saldo dos usuários'

    def handle(self, *args, **kwargs):
        agora = timezone.now()

        # Busca todos os créditos vencidos com saldo > 0
        vencidos = Credit.objects.filter(
            valid_until__lt=agora,
            valor_convertido__gt=0
        )

        if not vencidos.exists():
            self.stdout.write("Nenhum crédito vencido para expirar.")
            return

        # Agrupa créditos por usuário para atualizar saldo corretamente
        users = vencidos.values('user').distinct()

        for user_data in users:
            user_id = user_data['user']

            with transaction.atomic():
                user_credits = vencidos.filter(user_id=user_id)

                total_expirado = user_credits.aggregate(
                    total=Sum('valor_convertido')
                )['total'] or Decimal('0.00')

                if total_expirado > 0:
                    # Atualiza saldo do usuário
                    user = User.objects.get(id=user_id)
                    user.credito = max(user.credito - total_expirado, Decimal('0.00'))
                    user.save()

                    # Zera créditos expirados
                    user_credits.update(valor_convertido=0)

                    self.stdout.write(f"Usuário {user.id} - Créditos expirados: {total_expirado}")

        self.stdout.write("Processo de expiração concluído.")
