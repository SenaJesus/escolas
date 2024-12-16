import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_mailersend(smtp_host, smtp_port, usuario, senha, remetente, destinatario, assunto, corpo_html):
    """
    Envia um email utilizando o servidor SMTP especificado.

    Parâmetros:
    - smtp_host (str): Endereço do servidor SMTP.
    - smtp_port (int): Porta do servidor SMTP.
    - usuario (str): Nome de usuário para autenticação no servidor SMTP.
    - senha (str): Senha para autenticação no servidor SMTP.
    - remetente (str): Endereço de email do remetente.
    - destinatario (str): Endereço de email do destinatário.
    - assunto (str): Assunto do email.
    - corpo_html (str): Conteúdo do email em formato HTML.

    Processo:
    1. Cria uma mensagem multipart para suportar conteúdo HTML.
    2. Define os campos 'From', 'To' e 'Subject' da mensagem.
    3. Anexa o corpo do email em formato HTML.
    4. Conecta-se ao servidor SMTP e inicia uma conexão com STARTTLS.
    5. Realiza o login no servidor SMTP com as credenciais fornecidas.
    6. Envia o email.
    7. Encerra a conexão com o servidor SMTP.
    8. Imprime uma mensagem de sucesso ou erro no console.

    Retorna:
    - None
    """
    try:
        mensagem = MIMEMultipart()
        mensagem['From'] = remetente
        mensagem['To'] = destinatario
        mensagem['Subject'] = assunto

        mensagem.attach(MIMEText(corpo_html, 'html'))

        servidor = smtplib.SMTP(smtp_host, smtp_port)
        servidor.starttls()
        servidor.login(usuario, senha)

        servidor.sendmail(remetente, destinatario, mensagem.as_string())
        servidor.quit()

        print("E-mail enviado com sucesso!")
    except Exception as e:
        print(f"Erro ao enviar o e-mail: {e}")