import pytest

from src.zipdiff import zip_filenames_diff, zip_content_diff
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

EXPECTED_ZIP_FLAT_CONTENT = []
EXPECTED_ZIP_FLAT_WALK = []


def test_zip_with_non_existent_file(tmp_path):
    """Test zip_diff with a zip file containing a non-existent file."""

    with pytest.raises(FileNotFoundError):
        zip_filenames_diff(tmp_path / "non-existent.zip", tmp_path / "another-non-existent.zip")


def test_zip_diff_empty(tmp_path):
    """Test zip_diff with two empty zip files."""

    zip1 = create_test_zip(tmp_path, [], zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, [], zipfile_name="zip2.zip")

    diff = zip_filenames_diff(zip1, zip2)

    assert diff == set()


def test_zip_diff_same_file(tmp_path):
    """Test zip_diff with two zip files containing the same file."""

    content = [("file.txt", "This is a test file.")]
    zip1 = create_test_zip(tmp_path, content, zipfile_name="zip1.zip")

    diff = zip_filenames_diff(zip1, zip1)

    assert diff == set()


def test_zip_diff_flat(tmp_path):
    """Test zip_diff with two flat zip files."""

    zip1 = create_test_zip(tmp_path, ZIP_FLAT_01_CONTENT, zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, ZIP_FLAT_02_CONTENT, zipfile_name="zip2.zip")

    diff1 = zip_filenames_diff(zip1, zip2)
    diff2 = zip_filenames_diff(zip2, zip1)

    assert diff1 == {"file_1.txt", "B/file_3.txt"}
    assert diff2 == {"file_3.txt", "B/file_4.txt"}


def test_zip_content_diff_empty(tmp_path):
    """Test zip_content_diff with two empty zip files."""

    zip1 = create_test_zip(tmp_path, [], zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, [], zipfile_name="zip2.zip")

    diff = zip_content_diff(zip1, zip2)

    assert not diff


def test_zip_content_diff_same_file(tmp_path):
    """Test zip_content_diff with two zip files containing the same file."""

    content = [("file.txt", "This is a test file.")]
    zip1 = create_test_zip(tmp_path, content, zipfile_name="zip1.zip")

    diff = zip_content_diff(zip1, zip1)

    assert not diff


def test_zip_content_diff_flat(tmp_path):
    """Test zip_content_diff with two flat zip files."""

    zip1 = create_test_zip(tmp_path, ZIP_FLAT_01_CONTENT, zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, ZIP_FLAT_02_CONTENT, zipfile_name="zip2.zip")

    diff = zip_content_diff(zip1, zip2)

    assert diff == {
        "file_0.txt": "\n".join([
            "--- zip1.zip:file_0.txt",
            "+++ zip2.zip:file_0.txt",
            "@@ -1 +1 @@",
            "-Old",
            "+New"
        ]),
        "A/file_2.txt": "\n".join([
            "--- zip1.zip:A/file_2.txt",
            "+++ zip2.zip:A/file_2.txt",
            "@@ -1 +1 @@",
            "-Old",
            "+New"
        ])
    }
