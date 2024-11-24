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
2. Faça download dos modelos de validação de documentos:<br>
   `https://drive.google.com/drive/folders/1lvqSvpyaFFQPdTTnksAGkj_6GH2iHqCI?usp=sharing`
   
4. Crie a pasta `models` e copie os modelos para dentro
   
5. Renomeie os arquivos de ambiente:
   ```bash
   mv backend/env backend/.env
   mv env .env

6. Renomeie as variáveis dentro dso arquivos de ambiente para disparo de e-mail (backend/.env) e dados do banco de dados (/.env).
   
7. Inicie a aplicação com Docker Compose:
   ```bash
   docker-compose up --build

8. Acesse a aplicação em http://127.0.0.1:8000/api/
