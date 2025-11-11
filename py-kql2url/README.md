# kql2url

A simple Python utility to convert KQL queries into URLs.

## Installation

You can install the package using pip:

```bash
python -m pip install -e .
```

To install from git repository (without cloning the repository), use:

```bash
python -m pip install -e 'kql2url @ git+https://github.com/Robert-96/tools.git#subdirectory=py-kql2url'
```

## Usage

To display help information, run:

```bash
kql2url --help # Display help information
```

To convert a KQL query into a URL, use the following command:

```bash
kql2url --cluster <cluster_name> --database <database_name> --query "<KQL_query>"
```

To convert a KQL query from a file into a URL, use:

```bash
kql2url --cluster <cluster_name> --database <database_name> --kql-file <file_path>
```
