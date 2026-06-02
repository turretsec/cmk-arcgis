import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from cmk.agent_based.v2 import StringTable

T = TypeVar("T", bound=BaseModel)


def raw_section_text(string_table: StringTable) -> str:
    return "".join("".join(row) for row in string_table).strip()


def raw_json_from_string_table(string_table: StringTable) -> str:
    return raw_section_text(string_table)


def parse_json_section(
    string_table: StringTable,
    model: type[T],
) -> T | None:
    raw = raw_section_text(string_table)

    if not raw:
        return None

    try:
        return model.model_validate_json(raw)
    except ValidationError:
        return None
    except json.JSONDecodeError:
        return None
    
def raw_section_rows(string_table: StringTable) -> list[str]:
    """Each sep(0) row may be its own complete JSON document."""
    rows: list[str] = []

    for row in string_table:
        raw = "".join(row).strip()
        if raw:
            rows.append(raw)

    return rows


def looks_like_json_rows(rows: list[str]) -> bool:
    return bool(rows) and rows[0].startswith("{")
