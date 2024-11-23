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
   
2. Renomeie o arquivo de ambiente:
   ```bash
   mv backend/env backend/.env

3. Renomeie as variáveis dentro do arquivo de ambiente, para disparo de email.
   
4. Inicie a aplicação com Docker Compose:
   ```bash
   docker-compose up --build

5. Acesse a aplicação em http://127.0.0.1:8000/api/
