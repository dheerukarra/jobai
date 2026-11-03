import pytest

from jobai import db
from jobai.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, database_path=tmp_path / "t.sqlite3")


@pytest.fixture
def conn(settings):
    c = db.connect(settings.database_path)
    db.migrate(c)
    yield c
    c.close()
