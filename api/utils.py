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

def enviar_email_recuperacao(usuario, token):
    # Renderiza o template HTML com o contexto necessário
    context = {
        'nome': usuario.nome_completo,
        'link_recuperacao': os.getenv('FRONT_END_URL') + "/admin/recuperar-senha/{}".format(token),
    }

    message_html = render_to_string('email_template_recuperacao.html', context)

    # Enviar o email
    send_mail(
        subject="Recuperação de Senha!",
        message='Para redefinir sua senha, clique no botão abaixo.',  # Texto alternativo para clientes que não suportam HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        html_message=message_html  # Email em HTML
    )

def enviar_email_aprovacao(candidato, curso):
    context = {
        'nome': candidato.nome_completo,
        'nome_curso': curso.nome
    }
    
    message_html = render_to_string('email_template_aprovacao.html', context)

    # Enviar o email
    send_mail(
        subject="Sua inscrição foi aprovada!",
        message='Parabéns! Sua inscrição foi aprovada.',  # Texto alternativo para clientes que não suportam HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[candidato.email],
        html_message=message_html  # Email em HTML
    )

def enviar_email_rejeicao(candidato, curso, motivo, hash):
    context = {
        'nome': candidato.nome_completo,
        'nome_curso': curso.nome,
        'motivo_rejeicao': motivo,
        'link_alterar': os.getenv('FRONT_END_URL') + "/acesso/{}".format(hash),
    }

    message_html = render_to_string('email_template_rejeicao.html', context)

    send_mail(
        subject="Sua inscrição foi rejeitada!",
        message='Infelizmente, sua inscrição foi rejeitada.',  # Texto alternativo para clientes que não suportam HTML
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[candidato.email],
        html_message=message_html  # Email em HTML
    )
    