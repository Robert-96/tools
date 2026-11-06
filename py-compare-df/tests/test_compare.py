import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from src.compare import compare, compare_by_compare, compare_by_join, compare_by_merge


def test_merge_keeps_matched_and_unmatched_rows_only_when_requested():
    src = pd.DataFrame({"id": [1, 2, 3], "value": ["old", "same", "removed"]})
    dst = pd.DataFrame({"id": [1, 2, 4], "value": ["new", "same", "added"]})

    default = compare(src, dst, on=["id"])
    explicit_default = compare_by_merge(src, dst, on=["id"], keep_all=False)
    pd.testing.assert_frame_equal(default, explicit_default)
    assert dict(zip(default["id"], default["__status__"])) == {3: "Removed", 4: "Added"}

    result = compare(src, dst, on=["id"], keep_all=True).set_index("id")
    assert result.loc[1, ["value_x", "value_y", "__status__"]].tolist() == ["old", "new", "Both"]
    assert result.loc[2, ["value_x", "value_y", "__status__"]].tolist() == ["same", "same", "Both"]
    assert result.loc[3, "__status__"] == "Removed"
    assert result.loc[4, "__status__"] == "Added"


def test_merge_default_keys_empty_and_unmatched():
    src = pd.DataFrame({"id": [1], "value": ["old"]})
    dst = pd.DataFrame({"id": [1], "value": ["new"]})

    result = compare_by_merge(src, dst, keep_all=True)
    assert set(result["__status__"]) == {"Removed", "Added"}
    assert len(compare_by_merge(src, src)) == 0
    assert compare_by_merge(src, src, keep_all=True)["__status__"].tolist() == ["Both"]
    assert compare_by_merge(src.iloc[:0], dst.iloc[:0], keep_all=True).empty


def test_merge_keeps_duplicate_key_combinations():
    src = pd.DataFrame({"id": [1, 1], "value": ["a", "b"]})
    dst = pd.DataFrame({"id": [1, 1], "value": ["c", "d"]})

    result = compare_by_merge(src, dst, on=["id"], keep_all=True)
    assert set(zip(result["value_x"], result["value_y"])) == {
        ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d")
    }
    assert result["__status__"].tolist() == ["Both"] * 4
    assert compare_by_merge(src, dst, on=["id"]).empty


def test_join_keeps_existing_unchanged_classification():
    src = pd.DataFrame({"value": ["old", "same"]}, index=[1, 2])
    dst = pd.DataFrame({"value": ["new", "same"]}, index=[1, 3])

    default = compare(src, dst, method="join")
    pd.testing.assert_frame_equal(default, compare_by_join(src, dst, keep_all=False))
    result = compare(src, dst, method="join", keep_all=True)
    assert result.loc[1, ["value_src", "value_dst", "__status__"]].tolist() == ["old", "new", "Unchanged"]
    assert result.loc[2, "__status__"] == "Removed"
    assert result.loc[3, "__status__"] == "Added"
    assert 1 not in default.index


def test_join_preserves_existing_null_and_disjoint_column_classification():
    nulls = pd.DataFrame({"value": [None]})
    assert compare_by_join(nulls, nulls, keep_all=True).loc[0, "__status__"] == "Added"

    result = compare_by_join(pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}), keep_all=True)
    assert result.loc[0, "__status__"] == "Added"


def test_compare_keeps_full_shape_and_equal_values():
    src = pd.DataFrame({"value": ["old", "same"], "other": ["equal", "equal"]})
    dst = pd.DataFrame({"value": ["new", "same"], "other": ["equal", "equal"]})

    default = compare_by_compare(src, dst)
    expected_default = src.compare(dst, align_axis=0, keep_shape=False, keep_equal=False)
    pd.testing.assert_frame_equal(default, expected_default)
    with pytest.warns(UserWarning, match="'on' parameter"):
        result = compare(src, dst, method="compare", keep_all=True)
    expected = src.compare(dst, align_axis=0, keep_shape=True, keep_equal=True)
    pd.testing.assert_frame_equal(result, expected)
    assert result.loc[(1, "self"), "value"] == "same"
    assert result.loc[(0, "other"), "other"] == "equal"


def test_compare_still_requires_identical_labels():
    src = pd.DataFrame({"id": [1]})
    dst = pd.DataFrame({"id": [1, 2]})
    with pytest.raises(ValueError, match="identically-labeled"):
        compare_by_compare(src, dst, keep_all=True)


@pytest.mark.parametrize("keep_all", [False, True])
def test_cli_export_preserves_default_and_opt_in(tmp_path, keep_all):
    src = tmp_path / "source.csv"
    dst = tmp_path / "destination.csv"
    output = tmp_path / "result.csv"
    pd.DataFrame({"id": [1, 2], "value": ["old", "removed"]}).to_csv(src, index=False)
    pd.DataFrame({"id": [1, 3], "value": ["new", "added"]}).to_csv(dst, index=False)
    command = [
        sys.executable, "-m", "src", str(src), str(dst),
        "--on", "id", "--output", str(output),
    ]
    if keep_all:
        command.append("--keep-all")
    project_dir = Path(__file__).resolve().parents[1]
    subprocess.run(command, cwd=project_dir, check=True, capture_output=True, text=True)
    result = pd.read_csv(output).set_index("id")
    assert set(result["__status__"]) == ({"Both", "Added", "Removed"} if keep_all else {"Added", "Removed"})
    if keep_all:
        assert result.loc[1, ["value_x", "value_y"]].tolist() == ["old", "new"]
