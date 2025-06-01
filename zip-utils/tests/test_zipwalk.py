import io
import zipfile
from contextlib import redirect_stdout

import pytest

from src.zipwalk import zip_content, zip_tree, zip_walk
from tests.conftest import create_test_zip

ZIP_FLAT_CONTENT = [
    ("file_0.txt", "0"),
    ("file_1.txt", "1"),
    ("A/file_2.txt", "2"),
    ("B/file_3.txt", "3"),
]
EXPECTED_ZIP_FLAT_CONTENT = []
EXPECTED_ZIP_FLAT_WALK = []


ZIP_NESTED_CONTENT = [
    ("file_0.txt", "0"),
    ("file_1.txt", "1"),
    ("file_2.txt", "2"),
    ("A/file_3.txt", "3"),
    ("A/file_4.txt", "4"),
    ("B/file_5.txt", "5"),
    ("C/file_6.txt", "6"),
    ("C/D/file_7.txt", "7"),
    ("E/F/G", ""),
]
EXPECTED_NESTED_FLAT_CONTENT = []
EXPECTED_NESTED_FLAT_WALK = []


def test_zip_content_root(tmp_path):
    """Test zip_content for the root directory."""

    content = [
        ("file1.txt", "This is file 1"),
        ("file2.txt", "This is file 2"),
        ("dir1/file3.txt", "This is file 3"),
    ]
    zip_path = create_test_zip(tmp_path, content=content)

    dirnames, filenames = zip_content(zip_path)

    assert dirnames == {"dir1"}
    assert filenames == {"file1.txt", "file2.txt"}


def test_zip_content_subdirectory(tmp_path):
    """Test zip_content for a subdirectory."""

    content = [
        ("file1.txt", "This is file 1"),
        ("dir1/file2.txt", "This is file 2"),
        ("dir1/file3.txt", "This is file 3"),
        ("dir2/file4.txt", "This is file 4"),
    ]
    zip_path = create_test_zip(tmp_path, content=content)

    dirnames, filenames = zip_content(zip_path, path="dir1")

    assert dirnames == set()
    assert filenames == {"file2.txt", "file3.txt"}


def test_zip_content_empty_directory(tmp_path):
    """Test zip_content for an empty directory."""

    content = [
        ("file1.txt", "This is file 1"),
        ("empty_dir/", ""),
    ]
    zip_path = create_test_zip(tmp_path, content=content)

    dirnames, filenames = zip_content(zip_path, path="empty_dir")

    assert dirnames == set()
    assert filenames == set()


def test_zip_content_non_existent_path(tmp_path):
    """Test zip_content for a non-existent path."""
    content = [
        ("file1.txt", "This is file 1"),
        ("dir1/file2.txt", "This is file 2"),
    ]
    zip_path = create_test_zip(tmp_path, content=content)

    dirnames, filenames = zip_content(zip_path, path="nonexistent")

    assert dirnames == set()
    assert filenames == set()


def test_zip_walk_flat_structure(tmp_path):
    """Test zip_walk with a flat structure."""

    content = [
        ("file1.txt", "This is file 1"),
        ("file2.txt", "This is file 2"),
        ("dir1/file3.txt", "This is file 3"),
    ]
    zip_path = create_test_zip(tmp_path, content=content)

    result = list(zip_walk(zip_path))

    assert result == [
        ("/", {"dir1"}, {"file1.txt", "file2.txt"}),
        ("dir1", set(), {"file3.txt"}),
    ]


def test_zip_walk_empty_zip(tmp_path):
    """Test zip_walk with an empty zip file."""

    zip_path = tmp_path / "empty.zip"

    with zipfile.ZipFile(zip_path, 'w'):
        pass

    result = list(zip_walk(zip_path))

    assert result == [('/', set(), set())]


def test_zip_walk_non_existent_file():
    """Test zip_walk with a non-existent file."""

    with pytest.raises(FileNotFoundError):
        list(zip_walk("non_existent.zip"))


def test_zip_walk_invalid_zip(tmp_path):
    """Test zip_walk with an invalid zip file."""

    invalid_zip_path = tmp_path / "invalid.zip"
    invalid_zip_path.write_text("This is not a zip file")

    with pytest.raises(zipfile.BadZipFile):
        list(zip_walk(invalid_zip_path))


def test_zip_tree_subdirectory(tmp_path):
    content = [
        ("file1.txt", "This is file 1"),
        ("dir1/file2.txt", "This is file 2"),
        ("dir1/file3.txt", "This is file 3"),
        ("dir2/file4.txt", "This is file 4"),
    ]

    zip_path = create_test_zip(tmp_path, content=content)

    f = io.StringIO()
    with redirect_stdout(f):
        zip_tree(zip_path)
    result = f.getvalue().strip()

    assert result.startswith("test.zip\n")
    assert result.endswith("2 directories, 4 files")
