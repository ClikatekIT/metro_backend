# curriculum/management/commands/create_admin.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Cria um superusuário admin caso não exista.'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        # Verifica se já existe um superusuário
        if not User.objects.filter(is_superuser=True).exists():
            # Cria um superusuário com as credenciais fornecidas
            User.objects.create_superuser(
                name='admin',
                email='admin@example.com',
                password='adminpassword',
            )
            self.stdout.write(self.style.SUCCESS('Superusuário admin criado com sucesso!'))
        else:
            self.stdout.write(self.style.SUCCESS('Superusuário admin já existe.'))
