import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def enviar_email_mailersend(smtp_host, smtp_port, usuario, senha, remetente, destinatario, assunto, corpo_html):
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