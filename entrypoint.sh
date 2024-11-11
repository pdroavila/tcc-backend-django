#!/bin/sh

# Máximo de tentativas
MAX_TRIES=30
TRIES=0

while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
    TRIES=$((TRIES+1))
    if [ $TRIES -gt $MAX_TRIES ]; then
        echo "Erro: Não foi possível conectar ao banco de dados após $MAX_TRIES tentativas"
        exit 1
    fi
    echo "Aguardando banco de dados... (tentativa $TRIES de $MAX_TRIES)"
    sleep 1
done

echo "Banco de dados conectado!"

echo "Configuração atual do cron:"
cat /etc/cron.d/django-cron

chmod 0644 /etc/cron.d/django-cron
chmod +x /app/cron-script.sh

crontab /etc/cron.d/django-cron
echo "Crontab configurado:"
crontab -l

service cron start
service cron status

touch /var/log/cron.log
chmod 0644 /var/log/cron.log

# Verifica se a tabela django_migrations existe
TABLES=$(mysql -h $DATABASE_HOST -u $DATABASE_USER -p$DATABASE_PASSWORD $DATABASE_NAME -N -e "SHOW TABLES LIKE 'django_migrations';")

if [ -z "$TABLES" ]; then
    echo "Primeira execução detectada - Aplicando migrations iniciais..."
    python manage.py migrate

    echo "Executando comandos SQL iniciais..."
    mysql -h $DATABASE_HOST -u $DATABASE_USER -p$DATABASE_PASSWORD $DATABASE_NAME < /app/initial_setup.sql

else
    python manage.py migrate --check
    if [ $? -eq 0 ]; then
        echo "Sem migrations para aplicar"
    else
        echo "Aplicando novas migrations..."
        python manage.py migrate
    fi
fi

exec python manage.py runserver 0.0.0.0:8000
