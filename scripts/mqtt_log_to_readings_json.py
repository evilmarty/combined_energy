#!/usr/bin/env python3
"""Convert a text MQTT log into a JSON file of parsed readings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from pydantic import ValidationError

try:
    from custom_components.combined_energy.models import Readings
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from custom_components.combined_energy.models import Readings


READINGS_SUMMARY_HEADER = "periodEnd,periodDurationSecs,count"
READINGS_TOPIC_FRAGMENT = "/dmg/readings/"
TOPIC_LINE_RE = re.compile(r"^(?P<topic>\S+)\s(?P<payload>.*)$")


def iter_readings_messages(log_text: str):
    """Yield (topic, payload_text) for each readings message in the log."""
    current_topic: str | None = None
    current_payload_lines: list[str] = []

    for raw_line in log_text.splitlines():
        line = raw_line.rstrip("\n")
        topic_match = TOPIC_LINE_RE.match(line)
        if topic_match is not None and READINGS_TOPIC_FRAGMENT in topic_match.group(
            "topic"
        ):
            if current_topic is not None:
                yield current_topic, "\n".join(current_payload_lines)
            current_topic = topic_match.group("topic")
            current_payload_lines = [topic_match.group("payload")]
            continue

        if current_topic is not None:
            current_payload_lines.append(line)

    if current_topic is not None:
        yield current_topic, "\n".join(current_payload_lines)


def extract_readings_payload(payload_text: str) -> str:
    """Trim leading framing noise and return parseable readings content."""
    summary_start = payload_text.find(READINGS_SUMMARY_HEADER)
    if summary_start == -1:
        raise ValueError("No readings summary header found in message payload")
    return payload_text[summary_start:]


def convert_log_to_json(log_path: Path, output_path: Path) -> tuple[int, int]:
    """Parse readings messages in log_path and write output JSON file."""
    readings_json: list[dict[str, object]] = []
    failures = 0

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    for index, (topic, payload_text) in enumerate(
        iter_readings_messages(log_text), start=1
    ):
        try:
            payload = extract_readings_payload(payload_text)
            readings = Readings.from_mqtt_message(payload)
        except (ValueError, ValidationError):
            failures += 1
            continue

        readings_json.append(
            {
                "index": index,
                "topic": topic,
                "readings": readings.model_dump(mode="json", by_alias=True),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(readings_json, indent=2), encoding="utf-8")
    return len(readings_json), failures


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Convert a text MQTT log into JSON readings."
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        default="mosquitto.log",
        help="Path to the MQTT log file (default: mosquitto.log)",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        default="readings.json",
        help="Path to output JSON file (default: readings.json)",
    )
    return parser


def main() -> int:
    """CLI entrypoint."""
    parser = build_arg_parser()
    args = parser.parse_args()

    log_path = Path(args.log_file)
    output_path = Path(args.output_file)

    if not log_path.exists():
        sys.stderr.write(f"Log file not found: {log_path}\n")
        return 1

    parsed_count, failed_count = convert_log_to_json(log_path, output_path)
    sys.stdout.write(
        f"Wrote {parsed_count} readings messages to {output_path} "
        f"(skipped {failed_count} failed messages)\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
