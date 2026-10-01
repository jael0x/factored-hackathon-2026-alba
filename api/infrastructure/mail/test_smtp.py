from api.infrastructure.mail.smtp import LOGIN_CODE_SUBJECT, login_code_message


def test_login_code_message_names_code_and_validity() -> None:
    message = login_code_message("Alba <no-reply@alba.local>", "juan.romero@example.com", "481206")
    assert message["To"] == "juan.romero@example.com"
    assert message["Subject"] == LOGIN_CODE_SUBJECT
    body = message.get_content()
    assert "481206" in body
    assert "10 minutos" in body
