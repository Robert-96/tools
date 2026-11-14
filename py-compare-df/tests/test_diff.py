import json
import importlib
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import pytest

from src.diff import ReportRow, _report_rows, report_html as render_html, report_markdown as render_markdown


PROJECT_DIR = Path(__file__).resolve().parents[1]
diff_module = importlib.import_module("src.diff")


def report_rows(old, new, on, keep_all):
    result = diff_module.compare(old, new, method="join", on=on, keep_all=keep_all)
    return _report_rows(result, old, new, on)


def run_diff(*args):
    return subprocess.run(
        [sys.executable, "-m", "src.diff", *map(str, args)],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    )


@pytest.fixture
def inputs(tmp_path):
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    old.write_text("id,value,old_only\n1,old,a\n2,same,b\n3,removed,c\n", encoding="utf-8")
    new.write_text("id,value,new_only\n1,new,x\n2,same,y\n4,added,z\n", encoding="utf-8")
    return old, new


@pytest.mark.parametrize("extension", ["md", "html"])
@pytest.mark.parametrize("keep_all", [False, True])
def test_report_cli_join_keys_and_values(tmp_path, inputs, extension, keep_all):
    output = tmp_path / f"report.{extension}"
    args = [*inputs, "--on", "id", "--output", output]
    if keep_all:
        args.append("--keep-all")
    result = run_diff(*args)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert all(value in content for value in ["id=1", "Changed", "old", "new", "id=3", "Removed", "id=4", "Added"])
    status_text = "<td>Unchanged</td>" if extension == "html" else "| Unchanged |"
    assert (status_text in content) == keep_all
    expected_fields = ["old_only", "new_only"] if extension == "html" else [r"old\_only", r"new\_only"]
    assert all(field in content for field in expected_fields)


def test_report_index_and_input_immutability():
    old = pd.DataFrame({"value": ["old", "same"]}, index=["a", "b"])
    new = pd.DataFrame({"value": ["new", "same"]}, index=["a", "b"])
    old_copy, new_copy = old.copy(), new.copy()
    rows = report_rows(old, new, None, False)
    assert [(row.identity, row.status, row.values) for row in rows] == [
        ('"a"', "Changed", (("value", '"old"', '"new"'),))
    ]
    pd.testing.assert_frame_equal(old, old_copy)
    pd.testing.assert_frame_equal(new, new_copy)


@pytest.mark.parametrize("extension", [".md", ".html", ".diff"])
def test_diff_api_dispatches_and_returns_paths(tmp_path, monkeypatch, extension):
    old = pd.DataFrame({"value": ["old"]})
    new = pd.DataFrame({"value": ["new"]})
    old_copy, new_copy = old.copy(), new.copy()
    output = tmp_path / f"result{extension}"
    calls = []
    compare_calls = []
    result = pd.DataFrame({"value_old": ["from-result"], "value_new": ["result-new"], "__status__": ["Changed"]})

    def fake_compare(left, right, method, on, keep_all):
        compare_calls.append((left, right, method, on, keep_all))
        return result

    def fake_reporter(rows, title, on, keep_all):
        calls.append((rows, title, on, keep_all))
        return "content"

    monkeypatch.setattr(diff_module, "compare", fake_compare)
    monkeypatch.setitem(diff_module.reporters, extension, fake_reporter)
    options = {"keep_all": True}
    paths = diff_module.diff(old, new, output, **options)
    assert paths == output
    assert output.read_text(encoding="utf-8") == "content"
    assert len(calls) == 1
    assert len(compare_calls) == 1
    assert compare_calls[0][0] is old and compare_calls[0][1] is new
    assert compare_calls[0][2:] == ("join", None, True)
    assert calls[0][0][0].values == (("value", '"from-result"', '"result-new"'),)
    assert calls[0][1:] == ("DataFrame diff", None, True)
    pd.testing.assert_frame_equal(old, old_copy)
    pd.testing.assert_frame_equal(new, new_copy)


@pytest.mark.parametrize("extension", [".md", ".html", ".diff"])
def test_diff_passes_join_options_to_compare(tmp_path, monkeypatch, extension):
    old = pd.DataFrame({"id": [1], "value": ["old"]})
    new = pd.DataFrame({"id": [1], "value": ["new"]})
    calls = []
    actual_compare = diff_module.compare

    def recording_compare(left, right, method, on, keep_all):
        calls.append((left, right, method, on, keep_all))
        return actual_compare(left, right, method=method, on=on, keep_all=keep_all)

    monkeypatch.setattr(diff_module, "compare", recording_compare)
    diff_module.diff(old, new, tmp_path / f"report{extension}", on=["id"], keep_all=True)
    assert len(calls) == 1
    assert calls[0][0] is old and calls[0][1] is new
    assert calls[0][2:] == ("join", ["id"], True)


@pytest.mark.parametrize("extension", [".md", ".html", ".diff"])
def test_diff_api_produces_each_format_and_overwrites_existing_output(tmp_path, extension):
    old = pd.DataFrame({"id": [1], "value": ["old"]})
    new = pd.DataFrame({"id": [1], "value": ["new"]})
    output = tmp_path / f"result{extension}"
    options = {"on": ["id"]}
    paths = diff_module.diff(old, new, output, **options)
    assert output == paths
    assert output.exists()
    if extension == ".diff":
        assert output.read_text(encoding="utf-8").startswith("--- old\n+++ new\n")
    else:
        assert "Changed" in output.read_text(encoding="utf-8")
    output.write_text("stale", encoding="utf-8")
    assert diff_module.diff(old, new, output, **options) == paths
    assert output.read_text(encoding="utf-8") != "stale"


@pytest.mark.parametrize("extension", [".md", ".html"])
@pytest.mark.parametrize("keep_all", [False, True])
def test_report_context_escapes_title_and_keys(tmp_path, extension, keep_all):
    old = pd.DataFrame({"<id>": [1], "key|name": ["x"], "value": ["old"]})
    new = pd.DataFrame({"<id>": [1], "key|name": ["x"], "value": ["new"]})
    output = tmp_path / f"report{extension}"
    diff_module.diff(old, new, output, on=["<id>", "key|name"], keep_all=keep_all, title="<report> & name")
    content = output.read_text(encoding="utf-8")
    assert "&lt;report&gt; &amp; name" in content
    assert "&lt;id&gt;" in content
    if extension == ".html":
        assert "<title>&lt;report&gt; &amp; name</title>" in content
        assert "<h1>&lt;report&gt; &amp; name</h1>" in content
        assert "<strong>Matching:</strong> &lt;id&gt;, key|name" in content
        assert f"<strong>Include unchanged rows:</strong> {'Yes' if keep_all else 'No'}" in content
    else:
        assert "# &lt;report&gt; &amp; name" in content
        assert "**Matching:** &lt;id&gt;, key&#124;name" in content
        assert f"**Include unchanged rows:** {'Yes' if keep_all else 'No'}" in content


@pytest.mark.parametrize("extension", [".md", ".html"])
def test_report_defaults_display_index_matching_even_without_rows(tmp_path, extension):
    frame = pd.DataFrame({"value": [1]})
    output = tmp_path / f"report{extension}"
    diff_module.diff(frame, frame, output)
    content = output.read_text(encoding="utf-8")
    assert "DataFrame diff" in content
    assert "Matching:" in content and "Index" in content
    assert "Include unchanged rows:" in content and "No" in content


@pytest.mark.parametrize("extension", [".md", ".html"])
def test_cli_title_uses_only_input_names(tmp_path, extension):
    inputs_dir = tmp_path / "private-directory"
    inputs_dir.mkdir()
    old, new = inputs_dir / "old.csv", inputs_dir / "new.csv"
    old.write_text("value\nbefore\n", encoding="utf-8")
    new.write_text("value\nafter\n", encoding="utf-8")
    output = tmp_path / f"report{extension}"
    result = run_diff(old, new, "--output", output)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert "old.csv → new.csv" in content
    assert "private-directory" not in content


def test_custom_title_does_not_change_patch(tmp_path):
    old = pd.DataFrame({"value": ["old"]})
    new = pd.DataFrame({"value": ["new"]})
    output = tmp_path / "report.diff"
    diff_module.diff(old, new, output)
    original = output.read_bytes()
    diff_module.diff(old, new, output, title="Custom title")
    assert output.read_bytes() == original


def test_diff_api_rejects_unsupported_format_without_writing(tmp_path):
    frame = pd.DataFrame({"value": [1]})
    with pytest.raises(ValueError, match="Unsupported output format"):
        diff_module.diff(frame, frame, tmp_path / "result.txt")
    assert list(tmp_path.iterdir()) == []


def test_reporters_return_expected_content():
    old = pd.DataFrame({"id": [1], "value": ["old"]})
    new = pd.DataFrame({"id": [1], "value": ["new"]})
    rows = report_rows(old, new, ["id"], False)
    assert "Changed" in diff_module.report_markdown(rows)
    assert '<tr class="Changed">' in diff_module.report_html(rows)
    patch = diff_module.report_patch(rows)
    assert patch.startswith("--- old\n+++ new\n")
    assert '"keys": {"id": 1}' in patch


def test_cli_delegates_to_diff(tmp_path, monkeypatch, capsys):
    old_path = tmp_path / "old.csv"
    new_path = tmp_path / "new.csv"
    output = tmp_path / "report.md"
    old_path.write_text("value\nold\n", encoding="utf-8")
    new_path.write_text("value\nnew\n", encoding="utf-8")
    calls = []

    def fake_diff(old, new, path, on, keep_all, title):
        calls.append((old, new, path, on, keep_all, title))
        return path

    monkeypatch.setattr(diff_module, "diff", fake_diff)
    monkeypatch.setattr(sys, "argv", ["diff", str(old_path), str(new_path), "--output", str(output), "--keep-all"])
    diff_module.cli()
    assert len(calls) == 1
    assert calls[0][0]["value"].tolist() == ["old"]
    assert calls[0][1]["value"].tolist() == ["new"]
    assert calls[0][2:] == (output, None, True, "old.csv → new.csv")
    assert f"Diff written to: {output}" in capsys.readouterr().out


def test_html_and_markdown_escape_data():
    old = pd.DataFrame({"id": ["<script>"], "v|x": ["<img src=x onerror=alert(1)>"]})
    new = pd.DataFrame({"id": ["<script>"], "v|x": ["a|b\nc"]})
    rows = report_rows(old, new, ["id"], False)
    markup = render_html(rows)
    markdown = render_markdown(rows)
    assert "<script>" not in markup and "<img" not in markup
    assert "&lt;script&gt;" in markup and "&lt;img" in markup
    assert "&lt;script&gt;" in markdown and "v&#124;x" in markdown and r"a&#124;b\\nc" in markdown


def test_html_escapes_all_fields_and_rejects_invalid_status():
    row = ReportRow(
        '<row&"', "Changed", ("<field>",),
        {"values": {"<field>": '<old&"'}}, {"values": {"<field>": "<new>"}},
    )
    result = render_html([row])
    assert "&lt;row&amp;&#34;" in result
    assert "&lt;field&gt;" in result
    assert r"&lt;old&amp;\&#34;" in result
    assert "&lt;new&gt;" in result
    assert '<tr class="Changed">' in result
    with pytest.raises(ValueError, match="Unexpected join status"):
        render_html([ReportRow("row", 'Changed" onclick="alert(1)', ())])


def test_html_renders_status_without_value_columns():
    result = render_html([ReportRow("key", "Added", ())])
    assert '<th scope="row" class="row-identity">key</th>' in result
    assert "<td>Added</td>" in result
    assert "No fields differ among the displayed comparison rows." in result
    assert "<td>Old</td>" in result and "<td>New</td>" in result


def test_empty_report_and_nulls():
    empty = pd.DataFrame({"id": pd.Series(dtype="int64"), "value": pd.Series(dtype="object")})
    assert "No differences" in render_markdown(report_rows(empty, empty, ["id"], False))
    assert "No comparison rows were returned." in render_html(report_rows(empty, empty, ["id"], False))
    old = pd.DataFrame({"id": [1], "anchor": ["present"], "value": [None]})
    new = pd.DataFrame({"id": [1], "anchor": ["present"], "value": ["new"]})
    row = report_rows(old, new, ["id"], False)[0]
    assert ("value", "null", '"new"') in row.values


def test_composite_keys_and_suffix_names():
    old = pd.DataFrame({"id": [1], "date": ["a"], "code_old": ["before"]})
    new = pd.DataFrame({"id": [1], "date": ["a"], "code_old": ["after"]})
    row = report_rows(old, new, ["id", "date"], False)[0]
    assert row.identity == 'id=1, date="a"'
    assert row.values == (("code_old", '"before"', '"after"'),)


@pytest.mark.parametrize("equal", [False, True])
def test_unified_diff_file_contains_only_actual_changes(tmp_path, equal):
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    output = tmp_path / "change.diff"
    old.write_text(json.dumps([{"name": "é", "value": 1.2345678901234567}, {"name": "remove", "value": None}]), encoding="utf-8")
    new.write_text(old.read_text(encoding="utf-8") if equal else json.dumps(
        [{"name": "added", "value": 4}, {"name": "é", "value": 2}], ensure_ascii=False
    ), encoding="utf-8")
    result = run_diff(old, new, "--output", output)
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert content.startswith("--- old\n+++ new\n")
    assert not (tmp_path / "change.baseline.json").exists()
    if equal:
        assert content == "--- old\n+++ new\n"
    else:
        assert "@@" in content and '"name": "remove"' in content
        assert '"name": "added"' in content


def test_diff_json_rejects_infinite_values():
    row = ReportRow("x", "Changed", (), {"values": {"value": float("inf")}}, {"values": {"value": 1}})
    with pytest.raises(ValueError, match="infinite"):
        diff_module.report_patch([row])


def test_report_rows_reject_ambiguous_join_columns():
    old = pd.DataFrame({"value": [1], "value_new": [2]})
    new = pd.DataFrame({"value": [3]})
    result = pd.DataFrame([[1, 2, 3, "Changed"]], columns=["value_old", "value_new", "value_new", "__status__"])
    with pytest.raises(ValueError, match="unique column"):
        _report_rows(result, old, new, None)


def test_diff_json_preserves_float_precision():
    row = ReportRow("x", "Removed", ("value",), {"values": {"value": 1.2345678901234567}}, None)
    assert json.loads(diff_module.report_patch([row]).splitlines()[-1][1:])["values"]["value"] == 1.2345678901234567


def test_display_values_are_computed_from_records():
    old_values = {"old_only": None, "shared": "before", "literal": "—"}
    row = ReportRow(
        "key", "Changed", ("old_only", "shared", "new_only", "literal"),
        {"values": old_values},
        {"values": {"shared": None, "new_only": "after", "literal": "—"}},
    )
    assert row.values == (
        ("old_only", "null", "—"),
        ("shared", '"before"', "null"),
        ("new_only", "—", '"after"'),
        ("literal", '"—"', '"—"'),
    )
    old_values["shared"] = "updated"
    assert row.values[1] == ("shared", '"updated"', "null")


def test_html_caches_changed_fields(monkeypatch):
    row = ReportRow("key", "Changed", ("value",), {"values": {"value": "old"}}, {"values": {"value": "new"}})
    descriptor = ReportRow.__dict__["changed_fields"]
    original = descriptor.func
    calls = []

    def counting_changed_fields(instance):
        calls.append(1)
        return original(instance)

    monkeypatch.setattr(descriptor, "func", counting_changed_fields)
    html = render_html([row])
    assert len(calls) == 1
    assert html.count('class="changed-cell"') == 2
    assert row.changed_fields == {"value"}
    assert len(calls) == 1


@pytest.mark.parametrize("status", ["Added", "Removed"])
def test_display_values_preserve_fields_missing_from_one_side(status):
    old_record: dict[str, object] | None = {"values": {"old_only": "old"}} if status == "Removed" else None
    new_record: dict[str, object] | None = {"values": {"new_only": "new"}} if status == "Added" else None
    row = ReportRow("key", status, ("old_only", "new_only"), old_record, new_record)
    assert row.values == (
        ("old_only", '"old"' if old_record else "—", "—"),
        ("new_only", "—", '"new"' if new_record else "—"),
    )


class TableParser(HTMLParser):
    """Collect table rows and their rendered cells."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []
            self.tables.append(self.table)
        elif tag == "tr" and self.table is not None:
            self.row = []
            self.table.append(self.row)
        elif tag in ("td", "th") and self.row is not None:
            self.cell = {"text": "", "class": dict(attrs).get("class")}
            self.row.append(self.cell)

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.cell = None
        elif tag == "tr":
            self.row = None
        elif tag == "table":
            self.table = None


def parse_tables(html):
    parser = TableParser()
    parser.feed(html)
    return parser.tables


def test_html_tables_show_differences_and_paired_rows():
    old = pd.DataFrame({
        "id": [1, 2, 3], "value": ["old", "same", "removed"],
        "equal": [None, "equal", "equal"], "old_only": ["left", "left", "left"],
    })
    new = pd.DataFrame({
        "id": [1, 2, 4], "value": ["new", "same", "added"],
        "equal": [None, "equal", "equal"], "new_only": ["right", "right", "right"],
    })
    rows = report_rows(old, new, ["id"], True)
    html = render_html(rows)
    changes, all_fields = parse_tables(html)
    assert [cell["text"] for cell in all_fields[0]] == [
        "Row", "Status", "Side", "value", "equal", "old_only", "new_only"
    ]
    assert len(all_fields) == 1 + 2 * len(rows)
    for i, row in enumerate(rows):
        old_row, new_row = all_fields[1 + 2 * i:3 + 2 * i]
        assert [cell["text"] for cell in old_row[:3]] == [row.identity, row.status, "Old"]
        assert [cell["text"] for cell in new_row[:3]] == [row.identity, row.status, "New"]
        for field, old_cell, new_cell in zip(row.fields, old_row[3:], new_row[3:]):
            expected = "changed-cell" if field in row.changed_fields else None
            assert old_cell["class"] == new_cell["class"] == expected

    assert [(row[0]["text"], row[2]["text"]) for row in changes[1:]] == [
        (row.identity, field)
        for row in rows
        for field in row.fields if field in row.changed_fields
    ]
    first_old, first_new = all_fields[1:3]
    assert first_old[3]["text"] == '"old"*' and first_new[3]["text"] == '"new"*'
    assert first_old[4]["text"] == first_new[4]["text"] == "null"
    assert first_old[4]["class"] is None
    unchanged = next(row for row in rows if row.status == "Unchanged")
    assert unchanged.changed_fields == {"old_only", "new_only"}
    assert any(line[0]["text"] == unchanged.identity for line in changes[1:])
    assert 'aria-label="changed"' in html


def test_html_does_not_highlight_equal_rows_and_supports_duplicate_matches():
    same = pd.DataFrame({"value": ["same"]}, index=["unchanged"])
    html = render_html(report_rows(same, same, None, True))
    assert "No fields differ among the displayed comparison rows." in html
    table, = parse_tables(html)
    assert len(table) == 3
    assert all(cell["class"] in (None, "row-identity") for line in table for cell in line)

    old = pd.DataFrame({"value": ["old1", "old2"]}, index=["key", "key"])
    new = pd.DataFrame({"value": ["new1", "new2"]}, index=["key", "key"])
    markup = render_html(report_rows(old, new, None, False))
    assert "<dt>Changed Rows</dt><dd>4</dd>" in markup
    assert "<dt>Changed</dt><dd>4</dd>" in markup
    changes, all_fields = parse_tables(markup)
    assert len(changes) == 5
    assert len(all_fields) == 9


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ([], (0, 0, 0, 0)),
        (["Changed", "Added", "Removed", "Unchanged"], (4, 1, 1, 1)),
        (["Changed", "Changed", "Unchanged"], (3, 2, 0, 0)),
    ],
)
def test_html_status_summary_and_navigation(statuses, expected):
    rows = [ReportRow("duplicate", status, (), None, None) for status in statuses]
    html = render_html(rows)
    for label, count in zip(("Changed Rows", "Changed", "Added", "Removed"), expected):
        assert f"<dt>{label}</dt><dd>{count}</dd>" in html
    assert 'href="#changed-fields"' in html and 'id="changed-fields"' in html
    assert 'href="#all-fields"' in html and 'id="all-fields"' in html
    assert "Each count represents a comparison result. Some statuses may be inaccurate when values are missing or columns differ." in html
    assert "<script" not in html and 'rel="stylesheet"' not in html


def test_html_table_accessibility_and_empty_state():
    empty = render_html([])
    assert empty.count("No comparison rows were returned.") == 2
    old = pd.DataFrame({"value": ["old"]})
    new = pd.DataFrame({"value": ["new"]})
    html = render_html(report_rows(old, new, None, False))
    assert html.count('role="region"') == 2
    assert html.count('tabindex="0"') == 2
    assert '<caption class="sr-only">Changed fields with old and new values</caption>' in html
    assert '<caption class="sr-only">All fields, with old and new records on consecutive rows</caption>' in html
    assert 'aria-label="changed"' in html
    assert '<tr class="pair-start">' in html
    assert html.count('href="#top"') == 2
    assert 'id="top"' in html
    assert html.count('scope="col" class="row-identity"') == 2
    assert 'position: sticky;' in html


def test_html_field_comparison_uses_raw_values_and_presence():
    row = ReportRow(
        "key", "Changed", ("number", "null", "literal", "missing", "both_missing"),
        {"values": {"number": 1, "null": float("nan"), "literal": "—", "missing": None}},
        {"values": {"number": 1.0, "null": pd.NA, "literal": "—"}},
    )
    assert row.changed_fields == {"missing"}
    changes, all_fields = parse_tables(render_html([row]))
    assert [line[2]["text"] for line in changes[1:]] == ["missing"]
    assert all_fields[1][-2]["text"] == "null*"
    assert all_fields[2][-2]["text"] == "—*"
    assert all_fields[1][-1]["text"] == all_fields[2][-1]["text"] == "—"
    assert all_fields[1][-1]["class"] is None


def test_html_aligns_added_and_removed_rows_with_shared_schema():
    old = pd.DataFrame({"id": [1], "shared": ["old"], "first": [1]})
    new = pd.DataFrame({"id": [2], "shared": ["new"], "second": [2]})
    rows = report_rows(old, new, ["id"], False)
    assert [row.fields for row in rows] == [("shared", "first", "second")] * 2
    changes, all_fields = parse_tables(render_html(rows))
    assert [cell["text"] for cell in all_fields[0]] == ["Row", "Status", "Side", "shared", "first", "second"]
    assert all(len(line) == 6 for line in all_fields)
    assert [line[2]["text"] for line in changes[1:]] == ["shared", "first", "shared", "second"]
    assert all_fields[1][-1]["text"] == "—"
    assert all_fields[3][-2]["text"] == "—"


def test_html_schema_only_difference_obeys_join_filtering():
    old = pd.DataFrame({"id": [1], "shared": ["same"], "old_only": [None]})
    new = pd.DataFrame({"id": [1], "shared": ["same"]})
    filtered = report_rows(old, new, ["id"], False)
    assert filtered == []
    assert "<dt>Changed Rows</dt><dd>0</dd>" in render_html(filtered)
    retained = report_rows(old, new, ["id"], True)
    assert retained[0].status == "Unchanged"
    markup = render_html(retained)
    assert "<dt>Changed Rows</dt><dd>1</dd>" in markup
    changes, all_fields = parse_tables(markup)
    assert [line[2]["text"] for line in changes[1:]] == ["old_only"]
    assert all_fields[1][-1]["text"] == "null*"
    assert all_fields[2][-1]["text"] == "—*"


def test_patch_reports_join_rows_with_composite_keys_and_missing_values(tmp_path):
    old = pd.DataFrame({
        "id": [1, 2, 3], "group": ["é", "é", "é"],
        "value": ["old", "same", "removed"], "old_only": [None, "x", "y"],
    })
    new = pd.DataFrame({
        "id": [1, 2, 4], "group": ["é", "é", "é"],
        "value": ["new", "same", "added"], "new_only": ["—", "x", None],
    })
    output = tmp_path / "report.diff"
    diff_module.diff(old, new, output, on=["id", "group"], keep_all=True)
    lines = output.read_text(encoding="utf-8").splitlines()
    records = [(line[0], json.loads(line[1:])) for line in lines[2:] if line.startswith(("-", "+"))]
    assert records == [
        ("-", {"keys": {"id": 1, "group": "é"}, "values": {"value": "old", "old_only": None}}),
        ("+", {"keys": {"id": 1, "group": "é"}, "values": {"value": "new", "new_only": "—"}}),
        ("-", {"keys": {"id": 3, "group": "é"}, "values": {"value": "removed", "old_only": "y"}}),
        ("+", {"keys": {"id": 4, "group": "é"}, "values": {"value": "added", "new_only": None}}),
    ]
    assert [line for line in lines if line.startswith("@@")] == [
        "@@ -1,1 +1,1 @@", "@@ -2,1 +1,0 @@", "@@ -2,0 +2,1 @@",
    ]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["report.diff"]


def test_patch_reports_duplicate_matches_and_index_identity(tmp_path):
    old = pd.DataFrame({"value": ["old1", "old2"]}, index=["key", "key"])
    new = pd.DataFrame({"value": ["new1", "new2"]}, index=["key", "key"])
    output = diff_module.diff(old, new, tmp_path / "report.diff")
    lines = output.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line[1:]) for line in lines[2:] if line.startswith(("-", "+"))]
    assert len(records) == 8
    assert all(record["index"] == "key" for record in records)
    assert {(records[i]["values"]["value"], records[i + 1]["values"]["value"]) for i in range(0, 8, 2)} == {
        ("old1", "new1"), ("old1", "new2"), ("old2", "new1"), ("old2", "new2")
    }


def test_report_rows_preserve_large_integers_in_numeric_rows():
    old = pd.DataFrame({"large": [9007199254740993], "value": [1.5]})
    new = pd.DataFrame({"large": [9007199254740993], "value": [2.5]})
    patch = diff_module.report_patch(report_rows(old, new, None, False))
    records = [json.loads(line[1:]) for line in patch.splitlines()[3:]]
    assert all(record["values"]["large"] == 9007199254740993 for record in records)


def test_cli_patch_accepts_join_keys_and_keep_all(tmp_path, inputs):
    output = tmp_path / "report.diff"
    result = run_diff(*inputs, "--output", output, "--on", "id", "--keep-all")
    assert result.returncode == 0, result.stderr
    content = output.read_text(encoding="utf-8")
    assert '"keys": {"id": 1}' in content
    assert '"keys": {"id": 2}' not in content


def test_diff_output_preflight_and_force(tmp_path, inputs):
    output = tmp_path / "change.diff"
    output.write_text("existing", encoding="utf-8")
    result = run_diff(*inputs, "--output", output)
    assert result.returncode == 2 and "already exists" in result.stderr
    assert output.read_text(encoding="utf-8") == "existing"
    result = run_diff(*inputs, "--output", output, "--force")
    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding="utf-8").startswith("--- old\n+++ new\n")
    assert run_diff(*inputs, "--output", output).returncode == 2


def test_force_can_overwrite_input_via_symlink(tmp_path, inputs):
    old, new = inputs
    before = old.read_bytes()
    alias = tmp_path / "alias.md"
    alias.symlink_to(old)
    result = run_diff(old, new, "--output", alias)
    assert result.returncode == 2 and "already exists" in result.stderr
    assert old.read_bytes() == before
    result = run_diff(old, new, "--output", alias, "--on", "id", "--force")
    assert result.returncode == 0, result.stderr
    assert "# old.csv → new.csv" in old.read_text(encoding="utf-8")


def test_force_rejects_directory(tmp_path, inputs):
    output = tmp_path / "change.diff"
    output.mkdir()
    result = run_diff(*inputs, "--output", output, "--force")
    assert result.returncode == 2 and "directory" in result.stderr.lower()
    assert not (tmp_path / "change.baseline.json").exists()


def test_cli_rejects_dangling_symlink_without_force(tmp_path, inputs):
    output = tmp_path / "report.md"
    output.symlink_to(tmp_path / "missing")
    result = run_diff(*inputs, "--output", output)
    assert result.returncode == 2 and "already exists" in result.stderr
    assert not (tmp_path / "missing").exists()


def test_cli_rejects_invalid_formats_and_missing_keys(tmp_path, inputs):
    assert run_diff(*inputs, "--output", tmp_path / "result.txt").returncode == 2
    result = run_diff(*inputs, "--output", tmp_path / "result.html", "--on", "missing")
    assert result.returncode == 2 and "missing" in result.stderr
    unsupported = tmp_path / "data.txt"
    unsupported.write_text("data", encoding="utf-8")
    result = run_diff(unsupported, inputs[1], "--output", tmp_path / "result.md")
    assert result.returncode == 2 and "Unsupported import format" in result.stderr


def test_installed_wheel_includes_template_and_renders_outside_checkout(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "requirements.txt", "README.md"):
        shutil.copy(PROJECT_DIR / name, source / name)
    shutil.copytree(PROJECT_DIR / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__"))
    distributions = tmp_path / "distributions"
    distributions.mkdir()
    subprocess.run(
        [sys.executable, "-c", "import sys, setuptools.build_meta; setuptools.build_meta.build_sdist(sys.argv[1])",
         str(distributions)],
        cwd=source, check=True, capture_output=True, text=True,
    )
    with tarfile.open(next(distributions.glob("*.tar.gz")), "r:gz") as archive:
        assert any(name.endswith("/src/templates/diff.html") for name in archive.getnames())
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "--wheel-dir", str(wheels), str(source)],
        check=True, capture_output=True, text=True,
    )
    wheel = next(wheels.glob("py_compare_df-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        assert "py_compare_df/templates/diff.html" in archive.namelist()
        metadata_path = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        assert "requires-dist: jinja2" in archive.read(metadata_path).decode().lower()
    target = tmp_path / "installed"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(target), str(wheel)],
        check=True, capture_output=True, text=True,
    )
    old = tmp_path / "old.csv"
    new = tmp_path / "new.csv"
    report = tmp_path / "report.html"
    old.write_text("id,value\n1,old\n", encoding="utf-8")
    new.write_text("id,value\n1,new\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "py_compare_df.diff", str(old), str(new), "--on", "id", "--output", str(report)],
        cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(target)}, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert '<tr class="Changed">' in report.read_text(encoding="utf-8")
