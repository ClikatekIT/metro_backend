#!/bin/bash
# Script de setup inicial para o servidor Ubuntu (DigitalOcean Droplet)
# Corre este script como root na droplet

set -e

APP_DIR="/var/www/metro-backend"
REPO_URL="https://github.com/ClikatekIT/metro_backend.git"
DOMAIN="api.metrojobs.co.mz"

echo "=== 1. Actualizar sistema e instalar dependências ==="
apt update && apt upgrade -y
apt install -y \
    python3.12 python3.12-venv python3-pip \
    nginx \
    certbot python3-certbot-nginx \
    git \
    postgresql-client \
    wkhtmltopdf \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
    libssl-dev libpq-dev

echo "=== 2. Criar pasta da aplicação ==="
mkdir -p "$APP_DIR"
mkdir -p /var/log/gunicorn

echo "=== 3. Clonar repositório ==="
cd /var/www
git clone "$REPO_URL" metro-backend
cd "$APP_DIR"

echo "=== 4. Criar ambiente virtual ==="
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install gunicorn
pip install -r requirements.txt

echo "=== 5. Criar ficheiro .env ==="
echo "ATENÇÃO: Edita o ficheiro .env antes de continuar!"
echo "Copia o teu .env e o ficheiro de credenciais Google para $APP_DIR"
echo ""
echo "Variáveis obrigatórias no .env:"
cat << 'EOF'
SECRET_KEY=gera-uma-chave-segura-aqui
DEBUG=False
ALLOWED_HOSTS=api.metrojobs.co.mz
DB_NAME=metro
DB_USER=metro
DB_PASSWORD=a-tua-password
DB_HOST=24.199.100.234
DB_PORT=5432
OPENAI_API_KEY=
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=
MPESA_API_KEY=
MPESA_PUBLIC_KEY=
MPESA_SERVICE_PROVIDER_CODE=
MPESA_PRODUTION_URL=
GOOGLE_APPLICATION_CREDENTIALS=/var/www/metro-backend/metrojobs_django/mineral-brand-445417-v2-fd4c4b38aa6b.json
EOF

echo ""
read -p "Pressiona ENTER depois de criares o .env e copiares os ficheiros..."

echo "=== 6. Collectstatic e migrações ==="
source venv/bin/activate
python manage.py collectstatic --noinput
python manage.py migrate --run-syncdb

echo "=== 7. Permissões ==="
chown -R www-data:www-data "$APP_DIR"
chmod -R 755 "$APP_DIR"
# Protege o .env e as credenciais Google
chmod 600 "$APP_DIR/.env"
chmod 600 "$APP_DIR/metrojobs_django/mineral-brand-445417-v2-fd4c4b38aa6b.json"

echo "=== 8. Configurar Gunicorn como serviço systemd ==="
cp "$APP_DIR/deploy/gunicorn.service" /etc/systemd/system/metro-gunicorn.service
systemctl daemon-reload
systemctl enable metro-gunicorn
systemctl start metro-gunicorn
systemctl status metro-gunicorn

echo "=== 9. Configurar Nginx (sem SSL por agora) ==="
# Primeiro configurar sem SSL para poder obter o certificado
cat > /etc/nginx/sites-available/metro-api << 'NGINX'
server {
    listen 80;
    server_name api.metrojobs.co.mz;

    location /static/ {
        alias /var/www/metro-backend/staticfiles/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn/metro.sock;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/metro-api /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo "=== 10. Obter certificado SSL com Let's Encrypt ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@metrojobs.co.mz

echo "=== 11. Actualizar Nginx com config final (com SSL) ==="
cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/metro-api
nginx -t && systemctl reload nginx

echo ""
echo "=== DEPLOY CONCLUÍDO! ==="
echo "API disponível em: https://$DOMAIN"
echo ""
echo "Comandos úteis:"
echo "  Ver logs Gunicorn:   tail -f /var/log/gunicorn/metro-error.log"
echo "  Reiniciar Gunicorn:  systemctl restart metro-gunicorn"
echo "  Ver status:          systemctl status metro-gunicorn"
echo "  Reload Nginx:        systemctl reload nginx"
