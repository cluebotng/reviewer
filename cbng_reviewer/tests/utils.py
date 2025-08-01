from typing import List

from django.conf import settings
from django.db import connections


def load_sql_to_replica(sql_files: List[str]):
    sql_statements = []
    for sql_file in sql_files:
        with (settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "sql" / f"{sql_file}.sql").open("r") as fh:
            sql_statements.append(fh.read())

    with connections["replica"].cursor() as cursor:
        for sql in sql_statements:
            cursor.execute(sql)
