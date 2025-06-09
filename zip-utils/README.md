# ZipUtils

A command-line toolkit for inspecting, comparing, and visualizing ZIP file contents.

## Installation

```bash
pip install -e .
```

## Usage

Get help on version, available commands, or options:

```bash
zip-utils --version
zip-utils --help
zip-utils <command> --help
```

Display the structure of a ZIP file as a tree:

```bash
zip-utils tree <archive.zip>
```

Compare the contents of two ZIP files and show their differences:

```bash
zip-utils diff <archive1.zip> <archive2.zip>
```

Show the contents of a ZIP archive, optionally limited to a specific subpath:

```bash
zip-utils content <archive.zip> [sub/path]
```
