import subprocess
import sys
from pathlib import Path
import json

import pandas as pd
import pytest


PROJECT_DIR = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "src", *map(str, args)],
        cwd=PROJECT_DIR, capture_output=True, text=True,
    )


@pytest.mark.parametrize("keep_all", [False, True])
def test_cli_export_preserves_default_and_opt_in(tmp_path, keep_all):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / "result.csv"
    pd.DataFrame({"id": [1, 2], "value": ["old", "removed"]}).to_csv(src, index=False)
    pd.DataFrame({"id": [1, 3], "value": ["new", "added"]}).to_csv(dst, index=False)
    command = [
        sys.executable, "-m", "src", str(src), str(dst), "--method", "merge",
        "--on", "id", "--output", str(output),
    ]
    if keep_all:
        command.append("--keep-all")
    subprocess.run(command, cwd=PROJECT_DIR, check=True, capture_output=True, text=True)
    result = pd.read_csv(output).set_index("id")
    assert result.columns.tolist() == ["value_old", "value_new", "__status__"]
    assert set(result["__status__"]) == ({"Both", "Added", "Removed"} if keep_all else {"Added", "Removed"})
    if keep_all:
        assert result.loc[1, ["value_old", "value_new"]].tolist() == ["old", "new"]


@pytest.mark.parametrize("keep_all", [False, True])
def test_cli_join_composite_keys_are_exported(tmp_path, keep_all):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / "result.csv"
    src.write_text("id,date,value\n1,a,old\n2,b,same\n3,c,removed\n", encoding="utf-8")
    dst.write_text("id,date,value\n1,a,new\n2,b,same\n4,d,added\n", encoding="utf-8")
    args = [src, dst, "--method", "join", "--on", "id", "date", "--output", output]
    if keep_all:
        args.append("--keep-all")

    result = run_cli(*args)

    assert result.returncode == 0, result.stderr
    rows = pd.read_csv(output).set_index(["id", "date"])
    assert rows["__status__"].to_dict() == (
        {(1, "a"): "Changed", (2, "b"): "Unchanged", (3, "c"): "Removed", (4, "d"): "Added"}
        if keep_all else {(1, "a"): "Changed", (3, "c"): "Removed", (4, "d"): "Added"}
    )
    assert rows.loc[(1, "a"), ["value_old", "value_new"]].tolist() == ["old", "new"]


def test_cli_help():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "Compare two data files" in result.stdout
    assert "--keep-all" in result.stdout
    assert "--on" in result.stdout
    assert "--method" in result.stdout
    assert "default: merge" in result.stdout
    assert "{merge,join,compare}" in result.stdout


def test_cli_json_inputs_and_output(tmp_path):
    src = tmp_path / "source.json"
    dst = tmp_path / "destination.json"
    output = tmp_path / "result.json"
    src.write_text(json.dumps([{"id": 1}, {"id": 2}]), encoding="utf-8")
    dst.write_text(json.dumps([{"id": 1}, {"id": 3}]), encoding="utf-8")
    result = run_cli(src, dst, "--output", output)
    assert result.returncode == 0, result.stderr
    assert "Differences exported to:" in result.stdout
    rows = json.loads(output.read_text(encoding="utf-8"))
    assert {row["id"]: row["__status__"] for row in rows} == {2: "Removed", 3: "Added"}


@pytest.mark.parametrize("extension", ["xlsx", "md"])
def test_cli_excel_and_markdown_output(tmp_path, extension):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / f"result.{extension}"
    src.write_text("id\n1\n", encoding="utf-8")
    dst.write_text("id\n2\n", encoding="utf-8")

    result = run_cli(src, dst, "--output", output)
    assert result.returncode == 0, result.stderr
    if extension == "xlsx":
        rows = pd.read_excel(output)
        assert dict(zip(rows["id"], rows["__status__"])) == {1: "Removed", 2: "Added"}
    else:
        content = output.read_text(encoding="utf-8")
        assert "id" in content and "__status__" in content
        assert "Removed" in content and "Added" in content


def test_cli_debug_prints_differences(tmp_path):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    src.write_text("id\n1\n", encoding="utf-8")
    dst.write_text("id\n2\n", encoding="utf-8")
    result = run_cli(src, dst, "--debug")
    assert result.returncode == 0, result.stderr
    assert "__status__" in result.stdout
    assert "Added" in result.stdout and "Removed" in result.stdout


def test_cli_without_output_or_debug_is_silent(tmp_path):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    src.write_text("id\n1\n", encoding="utf-8")
    dst.write_text("id\n2\n", encoding="utf-8")
    result = run_cli(src, dst)
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_cli_rejects_unsupported_output_format(tmp_path):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    src.write_text("id\n1\n", encoding="utf-8")
    dst.write_text("id\n2\n", encoding="utf-8")
    result = run_cli(src, dst, "--output", tmp_path / "result.unknown")
    assert result.returncode == 2
    assert "Unsupported output format: unknown" in result.stderr


def test_cli_requires_input_files():
    result = run_cli()
    assert result.returncode == 2
    assert "required" in result.stderr


def test_cli_requires_valid_method():
    result = run_cli("first.csv", "second.csv", "--method", "invalid")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    assert "merge" in result.stderr and "join" in result.stderr and "compare" in result.stderr


def test_cli_rejects_positional_method(tmp_path):
    result = run_cli("merge", tmp_path / "first.csv", tmp_path / "second.csv")
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


@pytest.mark.parametrize("command", ["merge", "join", "compare"])
def test_cli_routes_each_comparison_method(tmp_path, command):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / "result.json"
    src.write_text("value\nold\n", encoding="utf-8")
    dst.write_text("value\nnew\n", encoding="utf-8")

    result = run_cli(src, dst, "--method", command, "--output", output)
    assert result.returncode == 0, result.stderr
    rows = json.loads(output.read_text(encoding="utf-8"))
    if command == "merge":
        assert {row["value"]: row["__status__"] for row in rows} == {"old": "Removed", "new": "Added"}
    elif command == "join":
        assert rows == [{"value_old": "old", "value_new": "new", "__status__": "Changed"}]
    else:
        assert rows == [{"value": "old"}, {"value": "new"}]
        assert result.stderr == ""


def test_cli_compare_warns_when_on_is_provided(tmp_path):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    src.write_text("value\nold\n", encoding="utf-8")
    dst.write_text("value\nnew\n", encoding="utf-8")
    result = run_cli(src, dst, "--method", "compare", "--on", "value", "--debug")
    assert result.returncode == 0
    assert "'on' parameter is not supported" in result.stderr
    assert "old" in result.stdout and "new" in result.stdout


@pytest.mark.parametrize("command", ["join", "compare"])
def test_cli_keep_all_for_other_methods(tmp_path, command):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / "result.json"
    src.write_text("value\nold\nsame\n", encoding="utf-8")
    dst.write_text("value\nnew\nsame\n", encoding="utf-8")
    result = run_cli(src, dst, "--method", command, "--keep-all", "--output", output)
    assert result.returncode == 0, result.stderr
    rows = json.loads(output.read_text(encoding="utf-8"))
    if command == "join":
        assert [row["__status__"] for row in rows] == ["Changed", "Unchanged"]
    else:
        assert [row["value"] for row in rows] == ["old", "new", "same", "same"]
