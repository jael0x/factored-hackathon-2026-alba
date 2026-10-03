import psycopg

from api.domain.products.product import CustomerProduct


class PostgresProducts:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def of_customer(self, customer_id: str) -> list[CustomerProduct]:
        rows = self._conn.execute(
            """
            SELECT product_id, product_type, product_number, currency, current_balance, product_status
            FROM products
            WHERE customer_id = %s
            ORDER BY product_id
            """,
            (customer_id,),
        ).fetchall()
        return [CustomerProduct(*row) for row in rows]
