from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import os

def enviar_email(candidato, hash, curso):
    # Renderiza o template HTML com o contexto necessário
    context = {
        'nome': candidato.nome_completo,
        'link_acesso': os.getenv('FRONT_END_URL') + "/acesso/{}".format(hash),
        'nome_curso': curso.nome
    }
    
    message_html = render_to_string('email_template.html', context)
    
    # Enviar o email
    send_mail(
        subject="Bem-vindo!",
        message='Obrigado por se cadastrar. Ative sua conta usando o link.',  # Texto alternativo para clientes que não suportam HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[candidato.email],
        html_message=message_html  # Email em HTML
    )