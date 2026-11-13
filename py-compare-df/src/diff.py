"""Generate reports from DataFrame comparisons."""

import argparse
import html
import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from functools import cached_property
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from .compare import compare
from .utils import import_df


def _display(value: object) -> str:
    """Format a cell or index value for inclusion in a report."""

    if value is None or value is pd.NA or value is pd.NaT or (isinstance(value, float) and pd.isna(value)):
        return "null"

    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)

    return str(value)


@dataclass(frozen=True)
class ReportRow:
    """A join result with its row identity and values from both inputs."""

    identity: str
    status: str
    fields: tuple[str, ...]
    old_record: dict[str, object] | None = None
    new_record: dict[str, object] | None = None

    @property
    def values(self) -> tuple[tuple[str, str, str], ...]:
        """Format both sides of each column for display."""

        old_fields = self.old_record["values"] if self.old_record is not None else {}
        new_fields = self.new_record["values"] if self.new_record is not None else {}

        if not isinstance(old_fields, dict) or not isinstance(new_fields, dict):
            raise TypeError("Report record values must be dictionaries.")

        return tuple(
            (
                field,
                _display(old_fields[field]) if field in old_fields else "—",
                _display(new_fields[field]) if field in new_fields else "—",
            )
            for field in self.fields
        )

    @cached_property
    def changed_fields(self) -> frozenset[str]:
        """Return fields that differ between the available records, cached on first access."""

        old_fields = self.old_record["values"] if self.old_record is not None else {}
        new_fields = self.new_record["values"] if self.new_record is not None else {}

        if not isinstance(old_fields, dict) or not isinstance(new_fields, dict):
            raise TypeError("Report record values must be dictionaries.")

        shared = [field for field in self.fields if field in old_fields and field in new_fields]
        old_values = pd.Series([old_fields[field] for field in shared], dtype=object)
        new_values = pd.Series([new_fields[field] for field in shared], dtype=object)

        old_null = old_values.isna()
        new_null = new_values.isna()

        equal = old_null & new_null
        non_null = ~(old_null | new_null)
        equal.loc[non_null] = old_values[non_null].eq(new_values[non_null]).fillna(False)
        changed = {field for field in self.fields if (field in old_fields) != (field in new_fields)}
        changed.update(field for field, matches in zip(shared, equal) if not matches)

        return frozenset(changed)


def _report_rows(
    result: pd.DataFrame, old: pd.DataFrame, new: pd.DataFrame, on: list[str] | None
) -> list[ReportRow]:
    """Prepare report rows from a join result and the input column schemas."""

    if not result.columns.is_unique or not old.columns.is_unique or not new.columns.is_unique:
        raise ValueError("Report requires unique column names after joining.")

    if not all(isinstance(column, str) for column in old.columns) or not all(
        isinstance(column, str) for column in new.columns
    ):
        raise ValueError("Report requires string column names.")

    keys = set(on or [])

    old_columns = [column for column in old.columns if column not in keys]
    new_columns = [column for column in new.columns if column not in keys]

    fields = tuple(dict.fromkeys([*old_columns, *new_columns]))
    shared = set(old_columns) & set(new_columns)

    expected = [*on] if on else []
    expected.extend(f"{field}_old" if field in shared else field for field in old_columns)
    expected.extend(f"{field}_new" if field in shared else field for field in new_columns)
    expected.append("__status__")

    if len(set(expected)) != len(expected) or set(expected) != set(result.columns):
        raise ValueError("Report cannot interpret ambiguous or unexpected join columns.")

    rows = []

    for index, values_tuple in zip(result.index, result.itertuples(index=False, name=None)):
        row = dict(zip(result.columns, values_tuple))
        status = row["__status__"]
        if status not in {"Added", "Removed", "Changed", "Unchanged"}:
            raise ValueError(f"Unexpected join status: {status}")
        identity = ", ".join(f"{key}={_display(row[key])}" for key in on) if on else _display(index)
        row_identity: dict[str, object] = {"keys": {key: row[key] for key in on}} if on else {"index": index}
        old_fields: dict[str, object] = {}
        new_fields: dict[str, object] = {}
        for field in fields:
            old_name = f"{field}_old" if field in shared else field
            new_name = f"{field}_new" if field in shared else field
            if field in old_columns and status != "Added":
                old_fields[field] = row[old_name]
            if field in new_columns and status != "Removed":
                new_fields[field] = row[new_name]
        old_record = {**row_identity, "values": old_fields} if status != "Added" else None
        new_record = {**row_identity, "values": new_fields} if status != "Removed" else None
        rows.append(ReportRow(identity, str(status), fields, old_record, new_record))

    return rows


def _escape_markdown(value: str) -> str:
    """Escape a value for a Markdown table cell."""

    escaped = html.escape(value).replace("\\", "\\\\")

    for character in "`*_[]":
        escaped = escaped.replace(character, f"\\{character}")

    return escaped.replace("|", "&#124;").replace("\n", "<br>").replace("\r", "&#13;")


def report_markdown(rows: list[ReportRow]) -> str:
    """Generate a Markdown report from the join comparison."""

    lines = [
        "# DataFrame diff",
        "",
        "Join statuses use a null/suffix heuristic; see the documentation for limitations.",
        "",
        "| Row | Status | Column | Old | New |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        for field, old_value, new_value in row.values or (("—", "—", "—"),):
            cells = (row.identity, row.status, field, old_value, new_value)
            lines.append("| " + " | ".join(_escape_markdown(cell) for cell in cells) + " |")

    if not rows:
        lines.extend(["", "No differences to display."])

    return "\n".join(lines) + "\n"


def report_html(rows: list[ReportRow]) -> str:
    """Generate an HTML report from the join comparison."""

    allowed = {"Added", "Removed", "Changed", "Unchanged"}
    for row in rows:
        if row.status not in allowed:
            raise ValueError(f"Unexpected join status: {row.status}")

    environment = Environment(
        loader=PackageLoader(__package__, "templates"),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )

    return environment.get_template("diff.html").render(rows=rows)


def _to_json(value: object) -> object:
    """Convert supported pandas and Python values into JSON-compatible values."""

    if value is None or value is pd.NA or value is pd.NaT:
        return None

    if isinstance(value, np.generic):
        return _to_json(value.item())

    if isinstance(value, float):
        if math.isnan(value):
            return None
        if not math.isfinite(value):
            raise ValueError("Cannot normalize infinite values to JSON.")

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (list, tuple)):
        return [_to_json(item) for item in value]

    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings.")

        return {key: _to_json(item) for key, item in value.items()}

    return value


def report_patch(rows: list[ReportRow]) -> str:
    """Render changed comparison rows as unified-style old/new JSON lines."""

    lines = ["--- old", "+++ new"]
    old_position = new_position = 0

    for row in rows:
        if row.status == "Unchanged":
            continue
        if row.status not in {"Added", "Removed", "Changed"}:
            raise ValueError(f"Unexpected join status: {row.status}")

        old_count = int(row.status != "Added")
        new_count = int(row.status != "Removed")

        if (old_count and row.old_record is None) or (new_count and row.new_record is None):
            raise ValueError("Comparison row is missing its old or new record.")

        lines.append(
            f"@@ -{old_position + old_count},{old_count} +{new_position + new_count},{new_count} @@"
        )

        if old_count:
            lines.append("-" + json.dumps(_to_json(row.old_record), ensure_ascii=False, allow_nan=False))
        if new_count:
            lines.append("+" + json.dumps(_to_json(row.new_record), ensure_ascii=False, allow_nan=False))

        old_position += old_count
        new_position += new_count

    return "\n".join(lines) + "\n"


Reporter = Callable[[list[ReportRow]], str]
reporters: dict[str, Reporter] = {
    ".md": report_markdown,
    ".html": report_html,
    ".diff": report_patch,
}


def diff(
    old: pd.DataFrame,
    new: pd.DataFrame,
    output: str | Path,
    on: list[str] | None = None,
    keep_all: bool = False,
) -> Path:
    """Compare DataFrames using join, write a report, and return its path.

    The output extension selects Markdown, HTML, or a unified-style diff.
    Existing files are overwritten.

    """

    output = Path(output)
    reporter = reporters.get(output.suffix.lower())

    if reporter is None:
        raise ValueError(f"Unsupported output format: {output.suffix or '(none)'}. Supported formats are: {', '.join(reporters.keys())}.")

    result = compare(old, new, method="join", on=on, keep_all=keep_all)
    report_rows = _report_rows(result, old, new, on)

    # for row in report_rows:
    #     if row.status == "Unchanged":
    #         continue

    #     print(f"Processing row with status: {row!r}")

    content = reporter(report_rows)

    with output.open("w", encoding="utf-8", newline="\n") as file:
        file.write(content)

    return output


def cli() -> None:
    """Run the standalone diff command."""

    parser = argparse.ArgumentParser(description="Generate a DataFrame comparison report.")

    parser.add_argument("old", type=Path, help="Original CSV or JSON file.")
    parser.add_argument("new", type=Path, help="Updated CSV or JSON file.")
    parser.add_argument("--output", type=Path, required=True, help=f"Output files with {', '.join(reporters.keys())} extensions.")
    parser.add_argument("--on", metavar="COLUMN", nargs="+", help="Join key columns.")
    parser.add_argument("--keep-all", action="store_true", help="Include unchanged rows in Markdown and HTML reports.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files.")

    args = parser.parse_args()

    output = Path(args.output)
    if (output.exists() or output.is_symlink()) and not args.force:
        parser.error(f"Output file '{output}' already exists. Use --force to overwrite.")

    try:
        old = import_df(args.old)
        new = import_df(args.new)
        written = diff(old, new, args.output, on=args.on, keep_all=args.keep_all)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"{parser.prog}: error: {exc}\n")

    print(f"Diff written to: {written}")


if __name__ == "__main__":
    cli()
