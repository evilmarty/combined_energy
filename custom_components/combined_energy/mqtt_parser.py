"""Parser for bridge MQTT readings payloads."""

from __future__ import annotations

from collections import defaultdict
import contextlib
import csv
import json
import re
from typing import Any

READINGS_BINARY_MARKER = rb"\n\x08readings\x10\x05B."


def _sanitize_payload(payload: bytes | str) -> str:
    """Decode payload and remove framing control characters."""
    if isinstance(payload, bytes):
        marker_match = re.search(READINGS_BINARY_MARKER, payload, flags=re.DOTALL)
        if marker_match is None:
            raise ValueError("No readings binary marker found in payload")
        payload = payload[marker_match.end() + 1 :]
        text = payload.decode("utf-8", errors="ignore")
    else:
        text = payload
    return "".join(
        char for char in text if char.isprintable() or char in {"\n", "\r", "\t"}
    )


def _parse_csv_line(line: str) -> list[str]:
    """Parse a single CSV line."""
    return next(csv.reader([line], skipinitialspace=True))


def _to_value(value: str) -> Any:
    """Convert a raw field string into a typed value."""
    if value == "!NULL":
        return None
    if value and value[0] == "{" and value[-1] == "}":
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(value)
    with contextlib.suppress(ValueError):
        return int(value)
    with contextlib.suppress(ValueError):
        return float(value)
    return value


def _parse_row(columns_line: str, values_line: str) -> dict[str, Any]:
    """Parse a keyed CSV row."""
    columns = _parse_csv_line(columns_line)
    values = _parse_csv_line(values_line)
    if len(values) < len(columns):
        values.extend([""] * (len(columns) - len(values)))
    return {
        column: _to_value(value) for column, value in zip(columns, values, strict=False)
    }


def _parse_sections(
    lines: list[str], start_index: int
) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Parse section blocks from the first section marker onwards."""
    records: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    i = start_index
    while i < len(lines):
        if lines[i] != "-" or i + 3 >= len(lines):
            i += 1
            continue
        section_type = lines[i + 1].split(",", 1)[0]
        records[section_type].append(_parse_row(lines[i + 2], lines[i + 3]))
        i += 4
    return dict(records), i


def parse_mqtt_readings_message(payload: bytes | str) -> dict[str, Any]:
    """Parse a single bridge readings message from payload content."""
    lines = [
        line.strip() for line in _sanitize_payload(payload).splitlines() if line.strip()
    ]
    if len(lines) < 2:
        raise ValueError("Invalid readings summary in payload")

    summary_row = _parse_row(lines[0], lines[1])
    expected_count = int(summary_row["count"])

    records, _ = _parse_sections(lines, 2)
    actual_count = sum(len(rows) for rows in records.values())
    if expected_count != actual_count:
        raise ValueError(
            f"Readings count mismatch: expected {expected_count}, parsed {actual_count}"
        )

    return {**summary_row, "records": records}
