from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session


KeyTuple = tuple[Any, ...]


def build_key(values: dict[str, Any], key_fields: Sequence[str]) -> KeyTuple:
    return tuple(values[field] for field in key_fields)


def fetch_existing_keys(
    session: Session,
    model: type[Any],
    key_fields: Sequence[str],
    keys: Iterable[KeyTuple],
) -> set[KeyTuple]:
    key_list = list(dict.fromkeys(keys))
    if not key_list:
        return set()

    columns = [getattr(model, field) for field in key_fields]
    return set(
        session.execute(
            select(*columns).where(tuple_(*columns).in_(key_list))
        ).all()
    )


def load_rows_by_keys(
    session: Session,
    model: type[Any],
    key_fields: Sequence[str],
    keys: Iterable[KeyTuple],
) -> list[Any]:
    key_list = list(dict.fromkeys(keys))
    if not key_list:
        return []

    columns = [getattr(model, field) for field in key_fields]
    return list(session.scalars(select(model).where(tuple_(*columns).in_(key_list))))


def upsert_rows(
    session: Session,
    model: type[Any],
    rows: Sequence[dict[str, Any]],
    key_fields: Sequence[str],
) -> None:
    if not rows:
        return

    dialect = session.bind.dialect.name if session.bind is not None else ""
    update_fields = [field for field in rows[0].keys() if field not in set(key_fields)]

    if dialect == "sqlite":
        for values in rows:
            statement = sqlite_insert(model).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=list(key_fields),
                set_={field: values[field] for field in update_fields},
            )
            session.execute(statement)
        return

    if dialect == "postgresql":
        for values in rows:
            statement = postgresql_insert(model).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=list(key_fields),
                set_={field: values[field] for field in update_fields},
            )
            session.execute(statement)
        return

    keys = [build_key(values, key_fields) for values in rows]
    existing_rows = {
        build_key({field: getattr(item, field) for field in key_fields}, key_fields): item
        for item in load_rows_by_keys(session, model, key_fields, keys)
    }
    for values in rows:
        key = build_key(values, key_fields)
        existing = existing_rows.get(key)
        if existing is None:
            session.add(model(**values))
            continue
        for field, value in values.items():
            if field in key_fields:
                continue
            setattr(existing, field, value)
