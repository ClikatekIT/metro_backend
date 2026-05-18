#!/bin/bash
# Script de actualização após git push
# Corre este script na droplet para actualizar a aplicação

set -e

APP_DIR="/var/www/metro-backend"

echo "=== A actualizar MetroJobs API ==="

cd "$APP_DIR"

echo "--- Pull do GitHub ---"
git pull origin main

echo "--- Instalar novas dependências (se houver) ---"
source venv/bin/activate
pip install -r requirements.txt

echo "--- Collectstatic ---"
python manage.py collectstatic --noinput

echo "--- Migrações ---"
python manage.py migrate

echo "--- Corrigir permissões ---"
chown -R www-data:www-data "$APP_DIR"

echo "--- Reiniciar Gunicorn ---"
systemctl restart metro-gunicorn

echo "=== Actualização concluída! ==="
systemctl status metro-gunicorn --no-pager
