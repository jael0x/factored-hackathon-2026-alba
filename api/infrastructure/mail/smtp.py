import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from api.contract_models import Locale
from api.infrastructure.config.settings import settings

SMTP_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class LoginCodeEmail:
    subject: str
    opening: str
    rules: tuple[str, ...]


LOGIN_CODE_EMAILS: dict[Locale, LoginCodeEmail] = {
    "es": LoginCodeEmail(
        subject="Tu código de Alba",
        opening="Tu código de Alba es {code}.",
        rules=(
            "Vale 10 minutos y sirve una sola vez. No lo compartas con nadie.",
            "Si no lo pediste, ignora este correo.",
        ),
    ),
    "pt": LoginCodeEmail(
        subject="Seu código Alba",
        opening="Seu código Alba é {code}.",
        rules=(
            "Ele vale por 10 minutos e só pode ser usado uma vez. Não o compartilhe com ninguém.",
            "Se você não pediu este código, ignore este e-mail.",
        ),
    ),
}


class Mailer(Protocol):
    def send_login_code(self, to: str, code: str, locale: Locale) -> None: ...


def login_code_message(sender: str, to: str, code: str, locale: Locale) -> EmailMessage:
    email = LOGIN_CODE_EMAILS[locale]
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = email.subject
    message.set_content("\n".join([email.opening.format(code=code), "", *email.rules, ""]))
    message["Content-Language"] = locale
    return message


class SmtpMailer:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self.host = host
        self.port = port
        self.sender = sender

    def send_login_code(self, to: str, code: str, locale: Locale) -> None:
        with smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.send_message(login_code_message(self.sender, to, code, locale))


def get_mailer() -> Mailer:
    return SmtpMailer(settings.smtp_host, settings.smtp_port, settings.mail_from)
