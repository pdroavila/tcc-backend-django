FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    netcat-traditional \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Definir o diretório de trabalho
WORKDIR /app

# Copiar os arquivos do projeto
COPY . /app

# Instalar dependências do Python
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o script de entrada
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expor a porta que o Django vai rodar
EXPOSE 8000

# Usar o entrypoint.sh como ponto de entrada
ENTRYPOINT ["/app/entrypoint.sh"]