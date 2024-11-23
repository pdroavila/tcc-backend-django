# Backend do TCC

Este repositório contém o código backend do meu TCC.

## Pré-requisitos

- Docker
- Docker Compose

## Configuração e Execução

1. Clone o repositório:
   ```bash
   git clone https://github.com/pdroavila/tcc-backend-django.git
   cd tcc-backend-django
2. Baixar os modelos de validação de documentos:<br>
   `https://drive.google.com/drive/folders/1lvqSvpyaFFQPdTTnksAGkj_6GH2iHqCI?usp=sharing`
3. Copiar os arquivos para /models/
   
4. Renomeie os arquivos de ambiente:
   ```bash
   mv backend/env backend/.env
   mv env .env

5. Renomeie as variáveis dentro dso arquivos de ambiente para disparo de e-mail (backend/.env) e dados do banco de dados (/.env).
   
6. Inicie a aplicação com Docker Compose:
   ```bash
   docker-compose up --build

7. Acesse a aplicação em http://127.0.0.1:8000/api/
