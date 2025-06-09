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


if __name__ == "__main__":
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
    tmp_path = Path("./data")
    tmp_path.mkdir(exist_ok=True)

    zip1 = create_test_zip(tmp_path, ZIP_FLAT_01_CONTENT, zipfile_name="zip1.zip")
    zip2 = create_test_zip(tmp_path, ZIP_FLAT_02_CONTENT, zipfile_name="zip2.zip")
