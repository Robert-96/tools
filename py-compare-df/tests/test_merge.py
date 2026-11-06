import pandas as pd
import pytest

from src.compare import compare, compare_by_merge


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


def test_merge_composite_keys_and_single_sided_columns():
    src = pd.DataFrame({"customer": [1, 1], "order": [1, 2], "before": ["a", "b"]})
    dst = pd.DataFrame({"customer": [1, 2], "order": [1, 1], "after": ["c", "d"]})
    result = compare_by_merge(src, dst, on=["customer", "order"], keep_all=True)
    rows = result.set_index(["customer", "order"])
    assert rows["__status__"].to_dict() == {(1, 1): "Both", (1, 2): "Removed", (2, 1): "Added"}
    assert rows.loc[(1, 1), ["before", "after"]].tolist() == ["a", "c"]
    assert result.columns.tolist() == ["customer", "order", "before", "after", "__status__"]


@pytest.mark.parametrize("empty_side,status", [("src", "Added"), ("dst", "Removed")])
def test_merge_one_empty_input(empty_side, status):
    rows = pd.DataFrame({"id": [1, 2]})
    empty = rows.iloc[:0]
    result = compare_by_merge(empty if empty_side == "src" else rows,
                              rows if empty_side == "src" else empty)
    assert result["id"].tolist() == [1, 2]
    assert result["__status__"].tolist() == [status, status]


def test_merge_duplicate_count_difference_is_not_reported():
    src = pd.DataFrame({"id": [1, 1]})
    dst = pd.DataFrame({"id": [1]})
    assert compare_by_merge(src, dst).empty
    result = compare_by_merge(src, dst, keep_all=True)
    assert result["__status__"].tolist() == ["Both", "Both"]
