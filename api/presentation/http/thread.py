from api.contract_models import ThreadMessage
from api.domain.process.case import ThreadLine


def wire_thread(lines: list[ThreadLine]) -> list[ThreadMessage]:
    return [
        ThreadMessage(id=line.line_id, author=line.author, body=line.body, event_id=line.event_id) for line in lines
    ]
