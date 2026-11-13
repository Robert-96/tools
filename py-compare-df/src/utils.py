"""Utility functions for importing and exporting pandas DataFrames."""

from pathlib import Path

import pandas as pd


def export_json(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to a JSON file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the JSON file will be saved.

    Returns:
        None

    """

    df.to_json(filepath, orient="records")


def export_jsonl(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to a JSON Lines file at the specified filepath.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the JSON Lines file will be saved.

    Returns:
        None

    """

    df.to_json(filepath, orient="records", lines=True)


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
    "jsonl": export_jsonl,
    "csv": export_csv,
    "xlsx": export_excel,
    "html": export_html,
    "md": export_markdown,
}


def export_df(df: pd.DataFrame, filepath: str | Path) -> None:
    """Exports the given pandas DataFrame to the appropriate format based on the file extension.

    Args:
        df: The pandas DataFrame to export.
        filepath: The path where the file will be saved.

    Returns:
        None

    """

    suffix = Path(filepath).suffix.lstrip(".").lower()
    exporter = exporters.get(suffix)

    if not exporter:
        raise ValueError(f"Unsupported export format: {suffix}. Supported formats are: {', '.join(exporters.keys())}.")

    exporter(df, filepath)


def import_json(filepath: str | Path) -> pd.DataFrame:
    """Imports a JSON file and returns it as a pandas DataFrame.

    Args:
        filepath: The path to the JSON file.

    Returns:
        A pandas DataFrame containing the data from the JSON file.

    """

    return pd.read_json(filepath)


def import_jsonl(filepath: str | Path) -> pd.DataFrame:
    """Imports a JSON Lines file and returns it as a pandas DataFrame.

    Args:
        filepath: The path to the JSON Lines file.

    Returns:
        A pandas DataFrame containing the data from the JSON Lines file.

    """

    return pd.read_json(filepath, orient="records", lines=True)


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
    "jsonl": import_jsonl,
    "csv": import_csv,
}


def import_df(filepath: str | Path) -> pd.DataFrame:
    """Imports a data file and returns it as a pandas DataFrame based on the file extension.

    Args:
        filepath: The path to the data file.

    Returns:
        A pandas DataFrame containing the data from the file.

    """

    suffix = Path(filepath).suffix.lstrip(".").lower()
    importer = importers.get(suffix)

    if not importer:
        raise ValueError(f"Unsupported import format: {suffix}. Supported formats are: {', '.join(importers.keys())}.")

    return importer(filepath)
