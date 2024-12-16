import random
import string
from django.utils import timezone
from .models import Autorizacao
from .email_service import enviar_email_mailersend
from django.template.loader import render_to_string
from django.conf import settings
from .jwt_utils import gerar_jwt

def gerar_codigo_confirmacao(length=6):
    """    
    Gera um código de confirmação aleatório composto por dígitos.

    Parâmetros:
    - length (int): O comprimento do código a ser gerado. Padrão é 6.

    Retorna:
    - str: O código de confirmação gerado.
    """
    return ''.join(random.choices(string.digits, k=length))

def enviar_email_confirmacao(email, codigo):
    """
    Envia um email de confirmação contendo o código gerado para o usuário.

    Parâmetros:
    - email (str): O endereço de email do destinatário.
    - codigo (str): O código de confirmação a ser enviado.

    Processo:
    1. Define o assunto do email.
    2. Renderiza o corpo do email utilizando um template HTML.
    3. Envia o email utilizando a função 'enviar_email_mailersend' com as configurações SMTP.
    """
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
    """
    Envia um email confirmando que a avaliação foi adicionada com sucesso para a escola especificada.

    Parâmetros:
    - email (str): O endereço de email do destinatário.
    - escola (Escola): A instância da escola que foi avaliada.

    Processo:
    1. Define o assunto do email.
    2. Renderiza o corpo do email utilizando um template HTML, passando os detalhes da escola.
    3. Envia o email utilizando a função 'enviar_email_mailersend' com as configurações SMTP.
    """
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
    """
    Cria ou atualiza uma autorização para o email fornecido com um novo código de confirmação.

    Parâmetros:
    - email (str): O endereço de email do usuário que está solicitando a autorização.

    Processo:
    1. Gera um novo código de confirmação utilizando 'gerar_codigo_confirmacao'.
    2. Atualiza ou cria uma instância de 'Autorizacao' no banco de dados com o email, código gerado,
       data de criação atual e marca como válida.
    3. Retorna o código de confirmação gerado.

    Retorna:
    - str: O código de confirmação gerado.
    """
    codigo = gerar_codigo_confirmacao()
    Autorizacao.objects.update_or_create(
        email=email,
        defaults={'codigo': codigo, 'data_criacao': timezone.now(), 'valido': True}
    )
    return codigo

def verificar_autorizacao(email, codigo):
    """
    Verifica se uma autorização válida existe para o email e código fornecidos.

    Parâmetros:
    - email (str): O endereço de email do usuário.
    - codigo (str): O código de confirmação a ser verificado.

    Retorna:
    - bool: True se a autorização for válida e não estiver expirada, False caso contrário.

    Processo:
    1. Tenta recuperar uma instância de 'Autorizacao' que corresponda ao email e código fornecidos e que esteja marcada como válida.
    2. Verifica se a autorização não expirou utilizando o método 'validar_expiracao' do modelo 'Autorizacao'.
    3. Retorna True se ambas as condições forem satisfeitas, ou False caso contrário.
    4. Se a autorização não existir, retorna False.
    """
    try:
        autorizacao = Autorizacao.objects.get(email=email, codigo=codigo, valido=True)
        if not autorizacao.validar_expiracao():
            return True
        return False
    except Autorizacao.DoesNotExist:
        return False

def gerar_token_para_email(email):
    """
    Gera um token JWT para o email fornecido.

    Parâmetros:
    - email (str): O endereço de email do usuário.

    Retorna:
    - str: O token JWT gerado.

    Processo:
    1. Utiliza a função 'gerar_jwt' para criar um token contendo o email e outras informações necessárias.
    2. Retorna o token JWT.
    """
    return gerar_jwt(email)