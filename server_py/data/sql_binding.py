"""query_engine.py builds SQL with named placeholders (@name). This converts
them to the pyformat named style (%(name)s) that snowflake-connector-python
(and Python's DB-API 2.0 generally) accepts directly alongside the same
params dict -- unlike the Node driver (server/src/data/sqlBinding.js's
positional ?-and-ordered-binds conversion), Python's connector supports
named substitution natively, so there's no need to build an ordered binds
list here.
"""

import re

_NAMED_PARAM = re.compile(r"@(\w+)")


def to_pyformat(sql: str, params: dict) -> str:
    """Converts @name -> %(name)s, validating every placeholder has a match
    in params (fails fast rather than letting the DB driver raise a less
    obvious KeyError deep in its own substitution logic)."""

    def replace(match: re.Match) -> str:
        name = match.group(1)
        if name not in params:
            raise KeyError(f'Missing bind parameter "{name}" for placeholder {match.group(0)}')
        return f"%({name})s"

    return _NAMED_PARAM.sub(replace, sql)
