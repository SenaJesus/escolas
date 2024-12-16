import jwt
from django.conf import settings
from datetime import datetime, timedelta

def gerar_jwt(email):
    """
    Gera um token JWT para o email fornecido.

    Parâmetros:
    - email (str): O endereço de email do usuário.

    Retorna:
    - str: O token JWT gerado.

    Processo:
    1. Define a data de expiração do token com base na configuração JWT_EXPIRATION_MINUTES.
    2. Cria o payload do token contendo o email, expiração e data de emissão.
    3. Codifica o token usando a chave secreta e o algoritmo HS256.
    4. Retorna o token JWT.
    """
    expiration = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)
    payload = {
        'email': email,
        'exp': expiration,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token

def verificar_jwt(token):
    """
    Verifica a validade de um token JWT.

    Parâmetros:
    - token (str): O token JWT a ser verificado.

    Retorna:
    - dict ou None: O payload do token se for válido, ou None se for inválido ou expirado.

    Processo:
    1. Decodifica o token usando a chave secreta e o algoritmo HS256.
    2. Retorna o payload se o token for válido.
    3. Captura exceções caso o token esteja expirado ou seja inválido e retorna None.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None