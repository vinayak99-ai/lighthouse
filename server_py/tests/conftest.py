import pytest

from ..data.db import ensure_schema, get_db
from ..data.seed import seed_all


@pytest.fixture(scope="session", autouse=True)
def _seeded_db():
    db = ensure_schema(get_db())
    row = db.execute("SELECT COUNT(*) c FROM stablecoin_supply").fetchone()
    if row["c"] == 0:
        seed_all()
    yield
