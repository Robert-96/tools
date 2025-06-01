"""This module provides utilities for comparing the contents of two zip files."""

import difflib
import zipfile
from pathlib import Path


def zip_diff(zip1_path, zip2_path):
    """Compare the file names in two zip files and return the differences.

    Args:
        zip1_path (str): Path to the first zip file.
        zip2_path (str): Path to the second zip file.

    Returns:
        set: A set of file names that are in zip1 but not in zip2.
    """

    with zipfile.ZipFile(zip1_path, 'r') as zip1, zipfile.ZipFile(zip2_path, 'r') as zip2:
        zip1_files = set(zip1.namelist())
        print(f"Files in {zip1_path}: {zip1_files}")

        zip2_files = set(zip2.namelist())
        print(f"Files in {zip2_path}: {zip2_files}")

        diff = zip1_files - zip2_files

        return diff


def zip_content_diff(zip1_path, zip2_path):
    """Compare the contents of two zip files and return a dictionary of differences.
    The keys are file names, and the values are the differences in content.

    Args:
        zip1_path (str): Path to the first zip file.
        zip2_path (str): Path to the second zip file.

    Returns:
        dict: A dictionary where keys are file names and values are the differences
              in content between the two zip files.
    """

    diff = {}
    zip1_name = Path(zip1_path).name
    zip2_name = Path(zip2_path).name

    with zipfile.ZipFile(zip1_path, 'r') as zip1, zipfile.ZipFile(zip2_path, 'r') as zip2:
        zip1_files = set(zip1.namelist())
        zip2_files = set(zip2.namelist())
        common_files = zip1_files & zip2_files

        for file in common_files:
            with zip1.open(file) as f1, zip2.open(file) as f2:
                content1 = f1.read().decode(errors="replace").splitlines()
                content2 = f2.read().decode(errors="replace").splitlines()

                if content1 != content2:
                    diff[file] = "\n".join(
                        difflib.unified_diff(
                            content1, content2,
                            fromfile=f"{zip1_name}:{file}",
                            tofile=f"{zip2_name}:{file}",
                            lineterm=""
                        )
                    )

    return diff
