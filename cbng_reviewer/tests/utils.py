import logging
from typing import Optional

from django.conf import settings
from django.db import connections
from django.test import TransactionTestCase

logger = logging.getLogger(__name__)


def replica_test_sql_file(file_name):
    def decorator(func):
        setattr(func, "_test_sql_file_name", file_name)
        return func

    return decorator


class WikipediaReplicaTransactionTestCase(TransactionTestCase):
    databases = {"default", "replica"}

    def setUp(self):
        super().setUp()
        self._load_sql_to_test_database()

    def _get_test_sql_file_name(self) -> Optional[str]:
        test_method = getattr(self, self._testMethodName)
        return getattr(test_method, "_test_sql_file_name", None)

    def _get_full_test_name(self) -> str:
        return f"{self.__class__.__name__}.{self._testMethodName}"

    def _load_sql_to_test_database(self):
        sql_files = []
        base_dir = settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "sql"

        schema_sql_file = (base_dir / "enwiki_p.sql").absolute()
        if schema_sql_file.exists():
            sql_files.append(schema_sql_file)
        else:
            raise RuntimeError(f"Missing schema SQL file: {schema_sql_file.as_posix()}")

        if test_sql_file_name := self._get_test_sql_file_name():
            test_sql_file = (base_dir / f"{test_sql_file_name}.sql").absolute()
            if test_sql_file.exists():
                sql_files.append(test_sql_file)
            else:
                raise RuntimeError(f"Missing test SQL file: {test_sql_file.as_posix()}")
        else:
            logger.warning(f"No replica SQL defined for: {self._get_full_test_name()}")

        sql_statements = []
        for sql_file in sql_files:
            with sql_file.open("r") as fh:
                sql_statements.append(fh.read())

        with connections["replica"].cursor() as cursor:
            for sql in sql_statements:
                cursor.execute(sql)
