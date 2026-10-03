import smtplib
from email.message import EmailMessage
from typing import get_args

import pytest

from api.contract_models import Locale
from api.infrastructure.mail.smtp import LOGIN_CODE_EMAILS, SmtpMailer, login_code_message

SENDER = "Alba <no-reply@alba.local>"


@pytest.mark.parametrize(
    ("locale", "subject", "validity"),
    [
        ("es", "Tu código de Alba", "Vale 10 minutos"),
        ("en", "Your Alba code", "valid for 10 minutes"),
        ("pt", "Seu código Alba", "vale por 10 minutos"),
    ],
)
def test_the_login_code_email_is_written_in_the_chosen_language(locale: Locale, subject: str, validity: str) -> None:
    message = login_code_message(SENDER, "juan.romero@example.com", "481206", locale)
    assert message["To"] == "juan.romero@example.com"
    assert message["Subject"] == subject
    assert message["Content-Language"] == locale
    body = message.get_content()
    assert "481206" in body
    assert validity in body


def test_every_language_has_a_login_code_email() -> None:
    assert set(LOGIN_CODE_EMAILS) == set(get_args(Locale))


def test_the_smtp_mailer_sends_the_email_in_the_chosen_language(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[EmailMessage] = []

    class RecordingSmtp:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            self.address = (host, port, timeout)

        def __enter__(self) -> "RecordingSmtp":
            return self

        def __exit__(self, *exc_info: object) -> None:
            return None

        def send_message(self, message: EmailMessage) -> None:
            sent.append(message)

    monkeypatch.setattr(smtplib, "SMTP", RecordingSmtp)
    SmtpMailer("mailpit", 1025, SENDER).send_login_code("juan.romero@example.com", "481206", "pt")
    assert [(message["To"], message["Subject"]) for message in sent] == [("juan.romero@example.com", "Seu código Alba")]
