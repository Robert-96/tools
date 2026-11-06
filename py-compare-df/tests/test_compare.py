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


def test_join_classifies_changed_unchanged_and_unmatched_rows():
    src = pd.DataFrame({"value": ["old", "same", "removed"]}, index=[1, 2, 3])
    dst = pd.DataFrame({"value": ["new", "same", "added"]}, index=[1, 2, 4])

    default = compare(src, dst, method="join")
    pd.testing.assert_frame_equal(default, compare_by_join(src, dst, keep_all=False))
    result = compare(src, dst, method="join", keep_all=True)
    assert result.loc[1, ["value_src", "value_dst", "__status__"]].tolist() == ["old", "new", "Changed"]
    assert result.loc[2, "__status__"] == "Unchanged"
    assert result.loc[3, "__status__"] == "Removed"
    assert result.loc[4, "__status__"] == "Added"
    assert default["__status__"].to_dict() == {1: "Changed", 3: "Removed", 4: "Added"}
    assert result.columns.tolist() == ["value_src", "value_dst", "__status__"]


def test_join_compares_shared_columns_with_null_values():
    src = pd.DataFrame({
        "anchor": ["present"] * 4,
        "first": [None, None, "old", "same"],
        "second": ["same", "same", "same", "old"],
        "source_only": [1] * 4,
    })
    dst = pd.DataFrame({
        "anchor": ["present"] * 4,
        "first": [None, "new", None, "same"],
        "second": ["same", "same", "same", "new"],
        "destination_only": [2] * 4,
    })

    result = compare_by_join(src, dst, keep_all=True)
    assert result["__status__"].tolist() == ["Unchanged", "Changed", "Changed", "Changed"]
    assert compare_by_join(src, dst).index.tolist() == [1, 2, 3]


def test_join_compares_actual_shared_column_names():
    src = pd.DataFrame({"code_src": ["old"], 1: ["same"], "source_only": ["left"]})
    dst = pd.DataFrame({"code_src": ["new"], 1: ["same"], "destination_only": ["right"]})
    result = compare_by_join(src, dst, keep_all=True)
    assert result["__status__"].tolist() == ["Changed"]
    assert result.loc[0, ["code_src_src", "code_src_dst"]].tolist() == ["old", "new"]


def test_join_compares_categorical_values_with_different_categories():
    src = pd.DataFrame({"value": pd.Categorical(["same", "old"], categories=["same", "old"])})
    dst = pd.DataFrame({"value": pd.Categorical(["same", "new"], categories=["same", "new"])})
    result = compare_by_join(src, dst, keep_all=True)
    assert result["__status__"].tolist() == ["Unchanged", "Changed"]


def test_join_handles_empty_inputs_and_multilevel_columns():
    empty = pd.DataFrame({"value": pd.Series(dtype="object")})
    assert compare_by_join(empty, empty).empty
    assert compare_by_join(empty, empty, keep_all=True).empty
    columns = pd.MultiIndex.from_tuples([("value", "nested")])
    src = pd.DataFrame([["old"]], columns=columns)
    dst = pd.DataFrame([["new"]], columns=columns)
    assert compare_by_join(src, dst, keep_all=True)["__status__"].iloc[0] == "Changed"


def test_join_on_matches_left_column_against_right_index():
    src = pd.DataFrame({"id": [10], "value": ["old"]})
    dst = pd.DataFrame({"value": ["new"]}, index=[10])
    result = compare(src, dst, method="join", on=["id"])
    assert result["__status__"].tolist() == ["Changed"]
    assert result[["value_src", "value_dst"]].iloc[0].tolist() == ["old", "new"]


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
