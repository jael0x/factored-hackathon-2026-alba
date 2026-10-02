from typing import TypeVar

Member = TypeVar("Member", bound=str)


def parse_member(value: object, members: frozenset[Member], label: str) -> Member:
    for member in members:
        if value == member:
            return member
    raise ValueError(f"{label} {value!r} is not one of {', '.join(sorted(members))}")
