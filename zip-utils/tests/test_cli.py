from typer.testing import CliRunner
import pytest

from src.cli import app
from tests.conftest import create_test_zip


ZIP_FLAT_01_CONTENT = [
    ("file_0.txt", "Old"),
    ("file_1.txt", "Old"),
    ("A/file_2.txt", "Old"),
    ("B/file_3.txt", "Old"),
]
ZIP_FLAT_02_CONTENT = [
    ("file_0.txt", "New"),
    ("file_3.txt", "New"),
    ("A/file_2.txt", "New"),
    ("B/file_4.txt", "New"),
]

runner = CliRunner()


@pytest.mark.parametrize("args", [
    [],
    ["--help"],
    ["--version"],
    ["-v"],
])
def test_cli_help_messages(args):
    result = runner.invoke(app, args)

    assert result.exit_code == 0, f"Output:\n {result.output}"
    assert result.output


def test_zip_diff(tmp_path):
    zip1 = create_test_zip(tmp_path, ZIP_FLAT_01_CONTENT, zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, ZIP_FLAT_02_CONTENT, zipfile_name="zip2.zip")

    result = runner.invoke(app, ["diff", str(zip1), str(zip2)])

    assert result.exit_code == 0, f"Output:\n {result.output}"
    assert result.output != ""
