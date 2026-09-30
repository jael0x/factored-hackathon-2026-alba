import smtplib
from email.message import EmailMessage
from typing import Protocol

from api.settings import settings

LOGIN_CODE_SUBJECT = "Tu código de Alba"
SMTP_TIMEOUT_SECONDS = 10


class Mailer(Protocol):
    def send_login_code(self, to: str, code: str) -> None: ...


def login_code_message(sender: str, to: str, code: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = LOGIN_CODE_SUBJECT
    message.set_content(
        f"Tu código de Alba es {code}.\n\n"
        "Vale 10 minutos y sirve una sola vez. No lo compartas con nadie.\n"
        "Si no lo pediste, ignora este correo.\n"
    )
    return message


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self.host = host
        self.port = port
        self.sender = sender

    def send_login_code(self, to: str, code: str) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.send_message(login_code_message(self.sender, to, code))


def get_mailer() -> Mailer:
    return SmtpMailer(settings.smtp_host, settings.smtp_port, settings.mail_from)
