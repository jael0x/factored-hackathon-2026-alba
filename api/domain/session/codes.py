import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

CODE_TTL = timedelta(seconds=600)
MAX_WRONG_CODES = 5
CODE_DIGITS = 6


@dataclass(frozen=True)
class IssuedCode:
    id: UUID
    code_hash: str
    expires_at: datetime
    wrong_codes: int
    used_at: datetime | None


@dataclass(frozen=True)
class CodeDelivery:
    email: str
    code: str


def new_code() -> str:
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def hash_code(secret: str, subject_id: str, code: str) -> str:
    return hmac.new(secret.encode(), f"{subject_id}:{code}".encode(), hashlib.sha256).hexdigest()


def code_is_open(issued: IssuedCode, now: datetime) -> bool:
    return issued.used_at is None and now < issued.expires_at and issued.wrong_codes < MAX_WRONG_CODES


def code_matches(secret: str, subject_id: str, issued: IssuedCode, code: str) -> bool:
    return hmac.compare_digest(issued.code_hash, hash_code(secret, subject_id, code))
