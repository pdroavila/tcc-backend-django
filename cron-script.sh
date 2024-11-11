#!/bin/bash

set -a
source /app/.env
set +a

export DATABASE_HOST=$(echo "${DATABASE_HOST}" | tr -d '\r')
export DATABASE_NAME=$(echo "${DATABASE_NAME}" | tr -d '\r')
export DATABASE_USER=$(echo "${DATABASE_USER}" | tr -d '\r')
export DATABASE_PASSWORD=$(echo "${DATABASE_PASSWORD}" | tr -d '\r')

log() {
    echo "[$(date)] $1" >> /var/log/cron.log
}

log_env_variables() {
    log "Verificando variáveis de ambiente:"
    log "DATABASE_HOST='${DATABASE_HOST}'"
    log "DATABASE_NAME='${DATABASE_NAME}'"
    log "DATABASE_USER='${DATABASE_USER}'"
    if [ -z "${DATABASE_PASSWORD}" ]; then
        log "DATABASE_PASSWORD não está definida."
    else
        log "DATABASE_PASSWORD está definida."
    fi
}

log_env_variables

max_retries=30
counter=0
log "Aguardando conexão com o banco de dados..."

until MYSQL_PWD="${DATABASE_PASSWORD}" mysql -h"${DATABASE_HOST}" -u"${DATABASE_USER}" --protocol=TCP -e "SELECT 1" >/dev/null 2>>/var/log/cron.log
do
    counter=$((counter + 1))
    if [ $counter -gt $max_retries ]; then
        log "Falha ao conectar ao banco de dados após $max_retries tentativas"
        exit 1
    fi
    log "Tentativa $counter de $max_retries - Aguardando banco de dados..."
    sleep 2
done

log "Conexão com o banco de dados estabelecida."

cd /app || { log "Falha ao mudar para o diretório /app"; exit 1; }

log "Executando comando Django"

export DJANGO_DB_HOST="$DATABASE_HOST"
export DJANGO_DB_PORT=3306

python manage.py shell << EOF
from api.tasks import update_expired_inscricoes
print("Iniciando update_expired_inscricoes")
try:
    update_expired_inscricoes()
    print("Finalizado update_expired_inscricoes")
except Exception as e:
    print(f"Erro ao atualizar inscrições: {str(e)}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    log "Comando Django executado com sucesso."
else
    log "Erro ao executar o comando Django."
    exit 1
fi
