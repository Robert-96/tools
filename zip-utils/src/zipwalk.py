"""A python script that walks through a zip file similar to the ``os.walk()`` function."""

import os
import zipfile
from pathlib import Path


def zip_content(zip_path, path=None):
    """Get the content of a zip file at a specific path. If the path is ``None``,
    it returns the content of the root directory.

    Args:
        zip_path (str): Path to the zip file.
        path (str): Path inside the zip file. If None, return the root content.

    Returns:
        tuple:  A tuple (dirnames, filenames) where:
            - ``dirnames`` is a set of directory names in the current directory.
            - ``filenames`` is a set of file names in the current directory.

    """

    with zipfile.ZipFile(zip_path, "r") as zf:
        if path is None:
            path = ""

        normalized_parent = path if path else "."

        all_names = zf.infolist()
        all_names = {item for item in all_names if str(Path(item.filename).parent) == normalized_parent}

        all_dirnames = {item.filename for item in all_names if item.is_dir()}
        all_filenames = {item.filename for item in all_names if not item.is_dir()}

        dirnames = {Path(name).name for name in all_dirnames if name != path}
        filenames = {Path(name).name for name in all_filenames if name != path}

        return dirnames, filenames


def zip_walk(zip_path):
    """Walk through a zip file similar to ``os.walk()``.

    Args:
        zip_path (str): Path to the zip file.

    Yields:
        tuple: A tuple (dirpath, dirnames, filenames) where:
            - ``dirpath`` is the current directory path inside the zip.
            - ``dirnames`` is a set of directory names in the current directory.
            - ``filenames`` is a set of file names in the current directory.

    """

    with zipfile.ZipFile(zip_path, 'r') as zf:
        all_names = zf.namelist()

        all_dirnames = {os.path.dirname(f) for f in all_names if f.endswith('/')}
        all_dirnames = sorted(all_dirnames)

        all_filenames = {f for f in all_names if not f.endswith('/')}
        all_filenames = sorted(all_filenames)

        yield "/", {d for d in all_dirnames if d != "/"}, {f for f in all_filenames if not os.path.dirname(f)}

        for dirpath in all_dirnames:
            if dirpath == "/":
                continue

            dirnames = {os.path.basename(d) for d in all_dirnames if os.path.dirname(d) == dirpath}
            filenames = {os.path.basename(f) for f in all_filenames if os.path.dirname(f) == dirpath}

            yield dirpath, dirnames, filenames


def zip_tree(zip_path, level=-1, dirs_only=False):
    """Walk through a zip file and prints the output.

    Args:
        zip_path (str): Path to the zip file.
        level (int): The level of the tree to print. If -1, print all levels.
        dirs_only (bool): If True, only print directories.

    """

    # prefix components:
    space =  '    '
    branch = '│   '

    # pointers:
    tee =    '├── '
    last =   '└── '

    def print_tree(dirpath, dirnames, filenames, prefix="  "):
        items = {{"name": dirname, "type": "dir"} for dirname in dirnames}
        items.update({{"name": filename, "type": "file"} for filename in filenames})
        items = sorted(items, key=lambda x: x["name"])

        if not items:
            return

        for dirname in sorted(dirnames):
            print(f"{prefix}├─ {dirname}/")

        for filename in sorted(filenames):
            print(f"{prefix}├─ {filename}")

    for dirpath, dirnames, filenames in zip_walk(zip_path):
        pass


def zip_cli():
    """Command line interface for the zip_walk function."""

    import argparse

    parser = argparse.ArgumentParser(description="Walk through a zip file and prints the output.")
    parser.add_argument("zip_path", help="Path to the zip file.")
    args = parser.parse_args()

    def print_tree(dirpath, dirnames, filenames, level=0):
        indent = "    " * level

        print(f"{indent}{os.path.basename(dirpath) if dirpath != '/' else '/'}")

        for dirname in sorted(dirnames):
            print(f"{indent}    {dirname}/")

        for filename in sorted(filenames):
            print(f"{indent}    {filename}")

    print(args.zip_path)
    for dirpath, dirnames, filenames in zip_walk(args.zip_path):

        level_map = {"/": 0}
        level = level_map.get(dirpath, 0)
        print_tree(dirpath, dirnames, filenames, level)
        for dirname in dirnames:
            level_map[os.path.join(dirpath, dirname)] = level + 1


if __name__ == "__main__":
    zip_cli()
