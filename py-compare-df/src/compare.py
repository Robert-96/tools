import argparse
from pathlib import Path
from warnings import warn
import pandas as pd


def compare_by_merge(
    src: pd.DataFrame, dst: pd.DataFrame, on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames and return the differences.

    Rows that are present in one DataFrame but not the other are marked as 'Added' or 'Removed'.

    The combined join keys should be unique within each DataFrame. Uniqueness
    is not enforced; duplicate keys can create multiple matches and hide
    differences in row counts. With on=None, all shared columns form the key.

    Args:
        src: The first pandas DataFrame.
        dst: The second pandas DataFrame.
        on: List of columns to join on. If None, defaults to the intersection of columns.
        keep_all: Retain matched rows as 'Both', even if their other values differ.

    Returns:
        A pandas DataFrame containing the differences between src and dst.

    """

    diff = pd.merge(src, dst, how="outer", indicator="__status__", on=on)
    statuses = {"left_only": "Removed", "right_only": "Added"}
    if keep_all:
        statuses["both"] = "Both"
    else:
        diff = diff.loc[diff["__status__"] != "both"]
    diff["__status__"] = diff["__status__"].map(statuses)

    return diff


def compare_by_join(
    src: pd.DataFrame, dst: pd.DataFrame, on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames using a join operation and return the differences.

    Rows that are present in one DataFrame but not the other are marked as 'Added' or 'Removed'.

    Args:
        src: The first pandas DataFrame.
        dst: The second pandas DataFrame.
        on: Left-side columns to join against the right index. If None, join on indexes.
        keep_all: Retain rows classified as 'Unchanged'. This status does not compare values.

    Returns:
        A pandas DataFrame containing the differences between src and dst.

    """

    diff = src.join(dst, how="outer", lsuffix="_src", rsuffix="_dst", on=on, sort=False)
    diff["__status__"] = diff.apply(
        lambda row: "Added" if pd.isna(row.filter(like="_src")).all() else ("Removed" if pd.isna(row.filter(like="_dst")).all() else "Unchanged"),
        axis=1,
    )
    if not keep_all:
        diff = diff.loc[diff["__status__"] != "Unchanged"]
    return diff


def compare_by_compare(
    src: pd.DataFrame, dst: pd.DataFrame, keep_all: bool = False, **kwargs
) -> pd.DataFrame:
    """Compare two pandas DataFrames using the built-in compare method and return the differences.

    Args:
        src: The first pandas DataFrame.
        dst: The second pandas DataFrame.
        keep_all: Retain all rows, columns, and equal values.

    Returns:
        A pandas DataFrame containing the differences between src and dst.
    """

    if "on" in kwargs:
        warn("The 'on' parameter is not supported when using the compare method.")

    diff = src.compare(dst, align_axis=0, keep_shape=keep_all, keep_equal=keep_all)
    return diff


commands = {
    "merge": compare_by_merge,
    "join": compare_by_join,
    "compare": compare_by_compare,
}


def compare(
    src: pd.DataFrame, dst: pd.DataFrame, method: str = "merge",
    on: list | None = None, keep_all: bool = False
) -> pd.DataFrame:
    """Compare two pandas DataFrames and return the differences using the specified method.

    Ensure the matching keys or index labels uniquely identify rows in each
    DataFrame. Uniqueness is not enforced; duplicates can lead to ambiguous
    comparisons. The matching rules depend on the selected method.

    Args:
        src: The first pandas DataFrame.
        dst: The second pandas DataFrame.
        method: The comparison method to use. Options are 'merge', 'join', or 'compare'.
        on: Merge keys or left join columns; not supported by the compare method.
        keep_all: Retain rows or equal values normally omitted by the selected method.

    Returns:
        A pandas DataFrame containing the differences between src and dst.

    """

    comparator = commands.get(method)

    if not comparator:
        raise ValueError(f"Unsupported comparison method: {method}. Supported methods are: {', '.join(commands.keys())}.")

    return comparator(src, dst, on=on, keep_all=keep_all)


def export_json(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to a JSON file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the JSON file will be saved.

    Returns:
        None
    """

    df.to_json(filepath, orient="records")


def export_csv(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to a CSV file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the CSV file will be saved.

    Returns:
        None

    """

    df.to_csv(filepath, index=False)


def export_excel(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to an Excel file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the Excel file will be saved.

    Returns:
        None

    """

    df.to_excel(filepath, index=False)


def export_html(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to an HTML file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the HTML file will be saved.

    Returns:
        None

    """

    df.to_html(filepath, index=False)


def export_markdown(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to a Markdown file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the Markdown file will be saved.

    Returns:
        None

    """

    with open(filepath, "w") as f:
        f.write(df.to_markdown(index=False, tablefmt="github"))


exporters = {
    "json": export_json,
    "csv": export_csv,
    "xlsx": export_excel,
    "html": export_html,
    "md": export_markdown,
}


def import_json(filepath: str | Path) -> pd.DataFrame:
    """Imports a JSON file and returns it as a pandas DataFrame.

    Args:
        filepath: The path to the JSON file.

    Returns:
        A pandas DataFrame containing the data from the JSON file.

    """

    return pd.read_json(filepath)


def import_csv(filepath: str | Path) -> pd.DataFrame:
    """Imports a CSV file and returns it as a pandas DataFrame.

    Args:
        filepath: The path to the CSV file.

    Returns:
        A pandas DataFrame containing the data from the CSV file.

    """

    return pd.read_csv(filepath)


importers = {
    "json": import_json,
    "csv": import_csv,
}


def cli():
    """Command-line interface for comparing JSON files."""

    parser = argparse.ArgumentParser(description="Compare two data files.")

    parser.add_argument("file1", help=f"Path to the first data file. Supported formats: [{', '.join(importers.keys())}].")
    parser.add_argument("file2", help=f"Path to the second data file. Supported formats: [{', '.join(importers.keys())}].")
    parser.add_argument("--on", metavar='COLUMN', type=str, nargs="+", help="List of columns to join on. If not provided, defaults to the intersection of columns.", required=False, default=None)
    parser.add_argument("--keep-all", action="store_true", help="Include rows with matching merge keys.")
    parser.add_argument("--output", help=f"Path to the output file. Supported formats: [{', '.join(exporters.keys())}].", required=False)
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.", required=False, default=False)

    args = parser.parse_args()

    data_file1 = Path(args.file1)
    data_file2 = Path(args.file2)

    df1 = importers.get(data_file1.suffix.lstrip(".").lower(), pd.read_json)(args.file1)
    df2 = importers.get(data_file2.suffix.lstrip(".").lower(), pd.read_json)(args.file2)

    debug = args.debug

    diff = compare(df1, df2, on=args.on, keep_all=args.keep_all)

    if debug:
        print(diff)

    if args.output:
        exporter = exporters.get(Path(args.output).suffix.lstrip(".").lower())

        if exporter:
            exporter(diff, args.output)
            print(f"Differences exported to: '{args.output}'")
        else:
            parser.error(f"Unsupported output format: {Path(args.output).suffix.lstrip('.').lower()}")


if __name__ == "__main__":
    cli()
