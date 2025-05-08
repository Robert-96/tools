"""A python script that walks through a zip file similar to the ``os.walk()`` function."""

import os
import zipfile


def zip_walk(zip_path):
    """Walk through a zip file similar to ``os.walk()``.

    Args:
        zip_path (str): Path to the zip file.

    Yields:
        tuple: A tuple (dirpath, dirnames, filenames) where:
            - ``dirpath`` is the current directory path inside the zip.
            - ``dirnames`` is a list of directory names in the current directory.
            - ``filenames`` is a list of file names in the current directory.

    """

    with zipfile.ZipFile(zip_path, 'r') as zf:
        all_files = zf.namelist()
        directories = {os.path.dirname(f) for f in all_files if f.endswith('/')}
        directories = sorted(directories)

        for dirpath in directories:
            dirnames = [os.path.basename(d) for d in directories if os.path.dirname(d) == dirpath]
            filenames = [os.path.basename(f) for f in all_files if os.path.dirname(f) == dirpath and not f.endswith('/')]
            yield dirpath, dirnames, filenames


def zip_cli():
    """Command line interface for the zip_walk function."""

    import argparse

    parser = argparse.ArgumentParser(description="Walk through a zip file and prints the output.")
    parser.add_argument("zip_path", help="Path to the zip file.")
    args = parser.parse_args()

    for dirpath, dirnames, filenames in zip_walk(args.zip_path):
        print(f"Directory: {dirpath}")
        print(f"Subdirectories: {dirnames}")
        print(f"Files: {filenames}")
        print()


if __name__ == "__main__":
    zip_cli()
