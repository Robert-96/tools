"""Zip utilities command line interface."""

import logging
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated
from rich.console import Console
from rich.syntax import Syntax

from src.zipdiff import zip_content_diff, zip_filenames_diff
from src.zipwalk import zip_tree
from src.__version__ import VERSION

logger = logging.getLogger(__name__)

console = Console()
app = typer.Typer(
    help="A command-line toolkit for inspecting, comparing, and visualizing ZIP file contents."
)
state = {"verbose": False}


def version_callback(value: bool):
    if value:
        print(f"zip-utils: {VERSION}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output.")] = False,
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True, help="Show the version of the CLI.")
    ] = None,
):
    """Zip utilities command line interface."""

    # Workaround for an issues with typer where it prints an empty error message if `no_args_is_help`
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())

    if verbose:
        print("Will write verbose output")
        state["verbose"] = True


@app.command("diff")
def zip_diff_cli(
    zip1: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    zip2: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
        ),
    ],
):
    """Compares the contents of two ZIP files and displays their differences."""

    print(f"Diff between {zip1} and {zip2}:")
    diff = zip_content_diff(zip1, zip2)

    for diff_string in diff.values():
        console.print(
            Syntax(diff_string, "diff")
        )


@app.command("tree")
def zip_tree_cli(
    zip1: Path,
    level: Annotated[int, typer.Option(min=-1, clamp=True)] = -1,
    dirs_only: Annotated[bool, typer.Option("--dirs-only")] = False
):
    """Display the structure of a zip file as a tree."""

    if level == 0:
        level = -1

    zip_tree(zip1, level=level, dirs_only=dirs_only)


@app.command("content")
def zip_content_cli(zip1: Path, subpath: Optional[str] = None):
    """Display the contents of a ZIP archive, optionally limited to a specific subpath."""

    pass


if __name__ == "__main__":
    app()
