"""Compare pandas DataFrames and export their differences."""

import argparse
from pathlib import Path
from warnings import warn

import pandas as pd

from .utils import export_df, exporters, import_df, importers


def compare_by_merge(
    old: pd.DataFrame, new: pd.DataFrame, on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames and return the differences.

    Rows that are present in one DataFrame but not the other are marked as 'Added' or 'Removed'.

    The combined join keys should be unique within each DataFrame. Uniqueness
    is not enforced; duplicate keys can create multiple matches and hide
    differences in row counts. With on=None, all shared columns form the key.

    Args:
        old: The original pandas DataFrame.
        new: The updated pandas DataFrame.
        on: List of columns to join on. If None, defaults to the intersection of columns.
        keep_all: Retain matched rows as 'Both', even if their other values differ.

    Returns:
        A pandas DataFrame containing the differences between old and new.

    """

    diff = pd.merge(old, new, how="outer", indicator="__status__", on=on, suffixes=("_old", "_new"))
    statuses = {"left_only": "Removed", "right_only": "Added"}
    if keep_all:
        statuses["both"] = "Both"
    else:
        diff = diff.loc[diff["__status__"] != "both"]
    diff["__status__"] = diff["__status__"].map(statuses)

    return diff


def compare_by_join(
    old: pd.DataFrame, new: pd.DataFrame, on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames using a join operation and return the differences.

    Rows classified as present on both sides are marked 'Changed' when shared
    columns differ, or 'Unchanged' otherwise. Two null values compare equal.
    Added and removed statuses use a null/suffix heuristic that can misclassify
    null-only rows or rows with disjoint columns.

    Args:
        old: The original pandas DataFrame.
        new: The updated pandas DataFrame.
        on: Columns in both DataFrames to join on. If None, join on indexes.
        keep_all: Retain rows classified as 'Unchanged' as well as differences.

    Returns:
        A pandas DataFrame containing the differences between old and new.

    """

    if on is not None:
        old = old.set_index(on)
        new = new.set_index(on)

    diff = old.join(new, how="outer", lsuffix="_old", rsuffix="_new", sort=False)
    column_labels = diff.columns.get_level_values(0) if isinstance(diff.columns, pd.MultiIndex) else diff.columns
    old_columns = diff.columns[[str(column).endswith("_old") for column in column_labels]]
    new_columns = diff.columns[[str(column).endswith("_new") for column in column_labels]]
    diff["__status__"] = diff.apply(
        lambda row: "Added" if pd.isna(row[old_columns]).all() else ("Removed" if pd.isna(row[new_columns]).all() else "Unchanged"),
        axis=1,
    )
    for column in old.columns.intersection(new.columns, sort=False):
        if isinstance(old.columns, pd.MultiIndex):
            old_column = (f"{column[0]}_old", *column[1:])
            new_column = (f"{column[0]}_new", *column[1:])
        else:
            old_column = f"{column}_old"
            new_column = f"{column}_new"
        old_values = diff[old_column]
        new_values = diff[new_column]
        if isinstance(old_values.dtype, pd.CategoricalDtype) or isinstance(new_values.dtype, pd.CategoricalDtype):
            old_values = old_values.astype(object)
            new_values = new_values.astype(object)
        equal = old_values.eq(new_values).fillna(False) | (old_values.isna() & new_values.isna())
        diff.loc[(diff["__status__"] == "Unchanged") & ~equal, "__status__"] = "Changed"
    if not keep_all:
        diff = diff.loc[diff["__status__"] != "Unchanged"]
    if on is not None:
        diff = diff.reset_index()
    return diff


def compare_by_compare(
    old: pd.DataFrame, new: pd.DataFrame, keep_all: bool = False, on: list | None = None, **kwargs
) -> pd.DataFrame:
    """Compare two pandas DataFrames using the built-in compare method and return the differences.

    Args:
        old: The original pandas DataFrame.
        new: The updated pandas DataFrame.
        keep_all: Retain all rows, columns, and equal values.

    Returns:
        A pandas DataFrame containing the differences between old and new.

    """

    if on is not None:
        old = old.set_index(on)
        new = new.set_index(on)

    diff = old.compare(new, align_axis=0, keep_shape=keep_all, keep_equal=keep_all, result_names=("old", "new"))
    return diff


commands = {
    "merge": compare_by_merge,
    "join": compare_by_join,
    "compare": compare_by_compare,
}


def compare(
    old: pd.DataFrame, new: pd.DataFrame, method: str = "merge",
    on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames and return the differences using the specified method.

    Ensure the matching keys or index labels uniquely identify rows in each
    DataFrame. Uniqueness is not enforced; duplicates can lead to ambiguous
    comparisons. The matching rules depend on the selected method.

    Args:
        old: The original pandas DataFrame.
        new: The updated pandas DataFrame.
        method: The comparison method to use. Options are 'merge', 'join', or 'compare'.
        on: Key columns for merge or join, or columns to use as indexes for
            compare. If None, each method uses its default matching.
        keep_all: Retain rows or equal values normally omitted by the selected method.

    Returns:
        A pandas DataFrame containing the differences between old and new.

    """

    comparator = commands.get(method)

    if not comparator:
        raise ValueError(f"Unsupported comparison method: {method}. Supported methods are: {', '.join(commands.keys())}.")

    return comparator(old, new, on=on, keep_all=keep_all)



def cli():
    """Command-line interface for comparing data files."""

    parser = argparse.ArgumentParser(description="Compare two data files.")

    parser.add_argument("file1", help=f"Path to the first data file. Supported formats: [{', '.join(importers.keys())}].")
    parser.add_argument("file2", help=f"Path to the second data file. Supported formats: [{', '.join(importers.keys())}].")
    parser.add_argument("--method", choices=commands, default="merge", help="Comparison method to use (default: merge).")
    parser.add_argument(
        "--on", metavar="COLUMN", nargs="+",
        help="Merge or join key columns; not supported by compare.",
    )
    parser.add_argument("--keep-all", action="store_true", help="Include rows or values normally omitted.")
    parser.add_argument("--output", help=f"Path to the output file. Supported formats: [{', '.join(exporters.keys())}].", required=False)
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False, default=False)

    args = parser.parse_args()

    df1 = import_df(args.file1)
    df2 = import_df(args.file2)

    diff = compare(df1, df2, method=args.method, on=args.on, keep_all=args.keep_all)

    debug = args.debug
    if debug:
        print(diff)

    if args.output:
        export_df(diff, args.output)


if __name__ == "__main__":
    cli()
