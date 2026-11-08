# py-compare-df

A Python tool for comparing pandas DataFrames and data files.

## Installation

Requires Python 3.10 or later. From the repository root:

```bash
python -m pip install ./py-compare-df
```

## Usage

Compare two CSV or JSON files and write the differences:

```bash
py-compare-df first.csv second.csv --output differences.csv
```

Use `--method` to select `merge` (default), `join`, or `compare`:

```bash
py-compare-df first.csv second.csv --method join --debug
```

Other options include `--on` for join keys and `--keep-all` to retain matches
or equal values normally omitted. Use `--output` to save results or `--debug`
to print them; without either, the command produces no output. Run
`py-compare-df --help` for all options. You can also use
`python -m py_compare_df`.

### Python API

```python
from py_compare_df import compare

result = compare(old=df1, new=df2, on=["id"], keep_all=True)
```

### Notes

- Keys should uniquely identify rows; duplicate keys can create multiple matches.
- `merge` matches shared columns by default. `--keep-all` retains matching
  keys as `Both`, even if other values differ.
- `join` uses indexes by default; `--on` matches columns in both inputs and
  includes the keys in the output. Its presence heuristic can misclassify
  key-only rows, null-only values, or disjoint non-key columns.
- `compare` requires identical index and column labels and does not support
  `--on`. Exporters omit its row labels; use `--debug` to inspect them.
