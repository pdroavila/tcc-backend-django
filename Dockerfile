FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    netcat-traditional \
    default-mysql-client \
    cron \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos do projeto
COPY . /app

# Instalar dependências do Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Configurar o cron - usando echo para evitar problemas de formato
RUN echo "PATH=/usr/local/bin:/usr/bin:/bin" > /etc/cron.d/django-cron \
    && echo "*/5 * * * * /app/cron-script.sh >> /var/log/cron.log 2>&1" >> /etc/cron.d/django-cron \
    && echo "" >> /etc/cron.d/django-cron \
    && chmod 0644 /etc/cron.d/django-cron \
    && crontab /etc/cron.d/django-cron

# Configurar o cron script
COPY cron-script.sh /app/cron-script.sh
RUN chmod +x /app/cron-script.sh \
    && dos2unix /app/cron-script.sh

# Criar arquivo de log para o cron
RUN touch /var/log/cron.log

# Copiar o script de entrada
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh \
    && dos2unix /app/entrypoint.sh

# Garantir que o arquivo .env está disponível e com as permissões corretas
RUN touch /app/.env && chmod 644 /app/.env

# Expor a porta que o Django vai rodar
EXPOSE 8000

# Usar o entrypoint.sh como ponto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]