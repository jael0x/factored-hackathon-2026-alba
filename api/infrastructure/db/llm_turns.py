from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from api.infrastructure.llm.conversation import LlmCall


# The row is written on its own connection, so it survives a failed attempt, which rolls back the command (E4).
class PostgresLlmTurns:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def record(self, call: LlmCall) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_turns (
                    process_id, command_id, request, raw_response, parsed, parse_ok, model,
                    input_tokens, output_tokens, latency_ms
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    call.process_id,
                    call.command_id,
                    Jsonb(dict(call.request)),
                    call.raw_response,
                    None if call.parsed is None else Jsonb(dict(call.parsed)),
                    call.parse_ok,
                    call.model,
                    call.input_tokens,
                    call.output_tokens,
                    call.latency_ms,
                ),
            )
