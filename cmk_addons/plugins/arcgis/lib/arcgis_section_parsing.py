from typing import TypeVar

from cmk.agent_based.v2 import StringTable
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def raw_section_rows(string_table: StringTable) -> list[str]:
    """Return one raw JSON document per sep(0) row.

    Checkmk may pass repeated sections as multiple rows. Do not concatenate them;
    each row can be a complete JSON document.
    """
    return [raw for row in string_table if (raw := "".join(row).strip())]


def parse_json_rows(
    string_table: StringTable,
    model: type[T],
) -> list[T]:
    return [model.model_validate_json(raw) for raw in raw_section_rows(string_table)]


def parse_last_json_row(
    string_table: StringTable,
    model: type[T],
    default: T,
) -> T:
    sections = parse_json_rows(string_table, model)
    return sections[-1] if sections else default
