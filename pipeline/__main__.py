from pipeline.batches import all_hashes_loaded, new_batch_id, record_batches
from pipeline.bronze import aws_s3_copy, ensure_bronze, raw_dir
from pipeline.checks import run_bronze_checks
from pipeline.db import connect, wait_for_postgres
from pipeline.gold import rebuild_gold
from pipeline.migrate import apply_migrations
from pipeline.report import report_load
from pipeline.silver import reload_silver


def main() -> None:
    wait_for_postgres()
    apply_migrations()
    files = ensure_bronze(raw_dir(), aws_s3_copy)
    run_bronze_checks(files)
    report_load(files)

    with connect() as conn:
        if all_hashes_loaded(conn, files):
            print("load_batches hashes match; skipping silver and gold reload")
            conn.commit()
            return

        batch_id = new_batch_id()
        print(f"loading silver and gold batch_id={batch_id}")
        with conn.transaction():
            reload_silver(conn, files)
            rebuild_gold(conn, batch_id)
            record_batches(conn, files, batch_id)
        print("load complete")


if __name__ == "__main__":
    main()
