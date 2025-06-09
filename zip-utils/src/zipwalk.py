"""A python script that walks through a zip file similar to the ``os.walk()`` function."""

import os
import zipfile
from itertools import islice
from pathlib import Path
from typing import Optional, Union


def zip_content(zip_path: Union[str, Path], path: Optional[Union[str, Path]] = None):
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


def zip_walk(zip_path: Union[str, Path]):
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


def zip_tree(zip_path: Union[str, Path], level: int = -1, dirs_only: bool = False, length_limit: int = 1000):
    """Walk through a zip file and prints the output.

    Args:
        zip_path (str): Path to the zip file.
        level (int): The level of the tree to print. If -1, print all levels.
        dirs_only (bool): If True, only print directories.
        length_limit (int): Maximum number of lines to print. If exceeded, truncates the output.

    """

    # prefix components:
    space = '    '
    branch = '│   '

    # pointers:
    tee = '├── '
    last = '└── '

    file_count = 0
    dir_count = 0

    def inner(zip_path: Path, path: Optional[Path] = None, prefix: str = '', level=-1):
        nonlocal file_count, dir_count

        if not level:
            return

        inner_dirs, inner_files = zip_content(zip_path, path=path)

        contents = {(inner_dir_path, True) for inner_dir_path in inner_dirs}
        if not dirs_only:
            contents |= {(inner_file_path, False) for inner_file_path in inner_files}

        # Create a list of pointers for tree visualization:
        # - Use `tee` for all items except the last one.
        # - Use `last` for the final item to indicate the end of a branch.
        pointers = [tee] * (len(contents) - 1) + [last]

        for pointer, (current_path, is_dir) in zip(pointers, contents):
            if is_dir:
                yield prefix + pointer + current_path
                dir_count += 1
                extension = branch if pointer == tee else space
                yield from inner(zip_path, current_path, prefix=prefix+extension, level=level-1)
            elif not dirs_only:
                file_count += 1
                yield prefix + pointer + current_path

    zip_path = Path(zip_path)
    print(zip_path.name)

    iterator = inner(zip_path, path=None, level=level)
    for line in islice(iterator, length_limit):
        print(line)

    if next(iterator, None):
        print(f'... length_limit, {length_limit}, reached, counted:')

    print(f"\n{dir_count} directories" + (f", {file_count} files" if file_count else ''))
