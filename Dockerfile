# Dockerfile for Django Backend
FROM python:3.12-slim

# Instale as dependências do sistema para compilar mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    libssl-dev \
    libmariadb-dev-compat \
    libmariadb-dev

# Defina o diretório de trabalho dentro do container
WORKDIR /app

# Copie o arquivo de requirements para instalar dependências
COPY requirements.txt /app/

# Instale as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o código da aplicação para o container
COPY . /app/

# Exponha a porta 8000
EXPOSE 8000

# Comando para rodar o servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
