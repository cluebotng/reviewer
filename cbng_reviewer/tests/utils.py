import hashlib
import logging
import uuid
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

        conn = connections["replica"]

        # Note: The database already has a `test_` prefix,
        #       set the name explicitly, to avoid a double prefix.
        #       Apply a random suffix to avoid conflicts if we run paralell tests
        instance = hashlib.sha256(uuid.uuid4().bytes).hexdigest()[-6:]
        conn.settings_dict["TEST"] |= {"NAME": f'{conn.settings_dict["NAME"]}_{instance}'}

        conn.creation.create_test_db(verbosity=0, autoclobber=True, keepdb=False)

        self._load_sql_to_test_database()

    def _get_test_sql_file_name(self) -> Optional[str]:
        test_method = getattr(self, self._testMethodName)
        return getattr(test_method, "_test_sql_file_name", None)

    def _get_full_test_name(self) -> str:
        return f"{self.__class__.__name__}.{self._testMethodName}"

    def _load_sql_to_test_database(self):
        sql_files = []
        base_dir = settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "sql"

        # Note: This is not exactly the same as the labs schema, which is built with views,
        #       but is compatible enough for test execution.
        for sql_file in (base_dir / "schema").glob("*.sql"):
            if sql_file.is_file():
                sql_files.append(sql_file)

        if not sql_files:
            raise RuntimeError("Missing SQL schema files")

        if test_sql_file_name := self._get_test_sql_file_name():
            test_sql_file = (base_dir / f"{test_sql_file_name}.sql").absolute()
            if test_sql_file.exists():
                sql_files.append(test_sql_file)
            else:
                raise RuntimeError(f"Missing test SQL file: {test_sql_file.as_posix()}")
        else:
            logger.debug(f"No replica SQL defined for: {self._get_full_test_name()}")

        sql_statements = []
        for sql_file in sql_files:
            with sql_file.open("r") as fh:
                sql_statements.append(fh.read())

        with connections["replica"].cursor() as cursor:
            for sql in sql_statements:
                cursor.execute(sql)
