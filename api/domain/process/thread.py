from typing import get_args

from api.contract_models import MessageAuthor

CUSTOMER_AUTHOR: MessageAuthor = "customer"
ASSISTANT_AUTHOR: MessageAuthor = "assistant"
TEMPLATE_AUTHOR: MessageAuthor = "template"
MESSAGE_AUTHORS: frozenset[MessageAuthor] = frozenset(get_args(MessageAuthor))
