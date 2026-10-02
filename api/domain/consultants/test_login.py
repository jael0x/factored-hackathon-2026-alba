import pytest

from api.domain.consultants.identity import ConsultantIdentity
from api.domain.consultants.login import ConsultantLoginKey, can_receive_code, login_key


def consultant(status: str) -> ConsultantIdentity:
    return ConsultantIdentity(
        "AGT-OJ9N4FGYV9", "E75612", "César", "González Sánchez", "cesar.gonzalez@example.com", status, "Créditos"
    )


def test_the_login_key_is_trimmed_with_the_email_in_lower_case_and_the_code_in_upper_case() -> None:
    assert login_key("  Cesar.Gonzalez@EXAMPLE.com \t", " e75612 ") == ConsultantLoginKey(
        "cesar.gonzalez@example.com", "E75612"
    )


def test_an_active_consultant_can_receive_a_code() -> None:
    assert can_receive_code(consultant("Active"))


@pytest.mark.parametrize("status", ["Vacation", "Leave", "Inactive"])
def test_a_consultant_who_is_not_active_cannot_receive_a_code(status: str) -> None:
    assert not can_receive_code(consultant(status))
