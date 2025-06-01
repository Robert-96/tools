import zipfile
from pathlib import Path


def create_test_zip(tmp_path, content, zipfile_name="test.zip"):
    """Util function to create a test zip file."""

    zip_path = tmp_path / zipfile_name

    with zipfile.ZipFile(zip_path, 'w') as zf:
        for item_path, item_content in content:
            item_path = Path(item_path)

            if item_path.is_dir():
                zf.mkdir(item_path)
                continue

            item_parent = str(item_path.parent)
            if item_parent and item_parent != "." and f"{item_parent}/" not in zf.namelist():
                zf.mkdir(item_parent)

            zf.writestr(str(item_path), item_content)

    return zip_path


def test_create_test_zip(tmp_path):
    """Test the create_test_zip function."""

    content = [
        ("file1.txt", "This is file 1"),
        ("dir1/file2.txt", "This is file 2"),
        ("dir1/dir2/file3.txt", "This is file 3"),
    ]
    zip_path = create_test_zip(tmp_path, content)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        assert set(zf.namelist()) == {
            "file1.txt",
            "dir1/",
            "dir1/file2.txt",
            "dir1/dir2/",
            "dir1/dir2/file3.txt",
        }
