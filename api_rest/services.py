import random
import string
from django.utils import timezone
from .models import Autorizacao
from .email_service import enviar_email_mailersend
from django.template.loader import render_to_string
from django.conf import settings
from .jwt_utils import gerar_jwt

def gerar_codigo_confirmacao(length=6):
    """Gera um código de confirmação aleatório."""
    return ''.join(random.choices(string.digits, k=length))

def enviar_email_confirmacao(email, codigo):
    assunto = "Código de Confirmação"
    corpo_html = render_to_string('email_confirmacao.html', {'codigo': codigo})
    enviar_email_mailersend(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        usuario=settings.SMTP_USER,
        senha=settings.SMTP_PASSWORD,
        remetente=settings.EMAIL_FROM,
        destinatario=email,
        assunto=assunto,
        corpo_html=corpo_html
    )

def enviar_email_confirmacao_avaliacao(email, escola):
    assunto = "Avaliação Adicionada com Sucesso"
    corpo_html = render_to_string('email_confirmacao_avaliacao.html', {'escola': escola})
    enviar_email_mailersend(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        usuario=settings.SMTP_USER,
        senha=settings.SMTP_PASSWORD,
        remetente=settings.EMAIL_FROM,
        destinatario=email,
        assunto=assunto,
        corpo_html=corpo_html
    )

def criar_ou_atualizar_autorizacao(email):
    codigo = gerar_codigo_confirmacao()
    Autorizacao.objects.update_or_create(
        email=email,
        defaults={'codigo': codigo, 'data_criacao': timezone.now(), 'valido': True}
    )
    return codigo

def verificar_autorizacao(email, codigo):
    try:
        autorizacao = Autorizacao.objects.get(email=email, codigo=codigo, valido=True)
        if not autorizacao.validar_expiracao():
            return True
        return False
    except Autorizacao.DoesNotExist:
        return False

def gerar_token_para_email(email):
    """
    Gera um JWT para o email.
    """
    return gerar_jwt(email)