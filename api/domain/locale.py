from typing import get_args

from api.contract_models import Locale

SPANISH_LOCALE: Locale = "es"
PORTUGUESE_LOCALE: Locale = "pt"
LOCALES: frozenset[Locale] = frozenset(get_args(Locale))
