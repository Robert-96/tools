import pandas as pd
import pytest

from src.compare import compare, compare_by_join


def test_join_classifies_changed_unchanged_and_unmatched_rows():
    src = pd.DataFrame({"value": ["old", "same", "removed"]}, index=[1, 2, 3])
    dst = pd.DataFrame({"value": ["new", "same", "added"]}, index=[1, 2, 4])

    default = compare(src, dst, method="join")
    pd.testing.assert_frame_equal(default, compare_by_join(src, dst, keep_all=False))
    result = compare(src, dst, method="join", keep_all=True)
    assert result.loc[1, ["value_old", "value_new", "__status__"]].tolist() == ["old", "new", "Changed"]
    assert result.loc[2, "__status__"] == "Unchanged"
    assert result.loc[3, "__status__"] == "Removed"
    assert result.loc[4, "__status__"] == "Added"
    assert default["__status__"].to_dict() == {1: "Changed", 3: "Removed", 4: "Added"}
    assert result.columns.tolist() == ["value_old", "value_new", "__status__"]


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
    assert result.loc[0, ["code_src_old", "code_src_new"]].tolist() == ["old", "new"]


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
    result = compare_by_join(src, dst, keep_all=True)
    assert result["__status__"].iloc[0] == "Changed"
    assert result.loc[0, [("value_old", "nested"), ("value_new", "nested")]].tolist() == ["old", "new"]


@pytest.mark.parametrize("column", ["code_old", "code_new"])
def test_join_suffix_in_input_name_does_not_hide_unmatched_rows(column):
    old = pd.DataFrame({column: ["before", "removed"]}, index=[1, 2])
    new = pd.DataFrame({column: ["after", "added"]}, index=[1, 3])
    result = compare_by_join(old, new, keep_all=True)
    assert result["__status__"].to_dict() == {1: "Changed", 2: "Removed", 3: "Added"}
    assert result.loc[1, [f"{column}_old", f"{column}_new"]].tolist() == ["before", "after"]


@pytest.mark.parametrize("keep_all", [False, True])
def test_join_on_matches_columns_without_mutating_inputs(keep_all):
    src = pd.DataFrame({"id": [1, 2, 3], "value": ["old", "same", "removed"]}, index=[8, 9, 10])
    dst = pd.DataFrame({"id": [1, 2, 4], "value": ["new", "same", "added"]}, index=[11, 12, 13])
    src_original = src.copy(deep=True)
    dst_original = dst.copy(deep=True)

    result = compare(src, dst, method="join", on=["id"], keep_all=keep_all)

    assert result.columns.tolist() == ["id", "value_old", "value_new", "__status__"]
    rows = result.set_index("id")
    assert rows["__status__"].to_dict() == (
        {1: "Changed", 2: "Unchanged", 3: "Removed", 4: "Added"}
        if keep_all else {1: "Changed", 3: "Removed", 4: "Added"}
    )
    assert rows.loc[1, ["value_old", "value_new"]].tolist() == ["old", "new"]
    pd.testing.assert_frame_equal(src, src_original)
    pd.testing.assert_frame_equal(dst, dst_original)


def test_join_on_composite_keys_and_duplicate_matches():
    src = pd.DataFrame({"id": [1, 1, 2], "date": ["a", "a", "b"], "value": ["old", "same", "removed"]})
    dst = pd.DataFrame({"id": [1, 1, 3], "date": ["a", "a", "c"], "value": ["new", "same", "added"]})
    result = compare_by_join(src, dst, on=["id", "date"], keep_all=True)

    assert result.columns.tolist() == ["id", "date", "value_old", "value_new", "__status__"]
    assert sorted(result.loc[result["id"] == 1, "__status__"]) == ["Changed", "Changed", "Changed", "Unchanged"]
    assert result.loc[result["id"] == 2, "__status__"].item() == "Removed"
    assert result.loc[result["id"] == 3, "__status__"].item() == "Added"
    assert result.loc[result["id"] == 2, "date"].item() == "b"
    assert result.loc[result["id"] == 3, "date"].item() == "c"


@pytest.mark.parametrize("missing_side", ["src", "dst"])
def test_join_on_requires_keys_in_both_inputs(missing_side):
    with_key = pd.DataFrame({"id": [1], "value": ["x"]})
    without_key = pd.DataFrame({"value": ["x"]}, index=pd.Index([1], name="id"))
    src, dst = (without_key, with_key) if missing_side == "src" else (with_key, without_key)
    with pytest.raises(KeyError, match="id"):
        compare_by_join(src, dst, on=["id"])


def test_join_on_empty_inputs_retains_key_column():
    empty = pd.DataFrame({"id": pd.Series(dtype="int64"), "value": pd.Series(dtype="object")})
    result = compare_by_join(empty, empty, on=["id"], keep_all=True)
    assert result.empty
    assert result.columns.tolist() == ["id", "value_old", "value_new", "__status__"]


def test_join_on_key_only_preserves_existing_presence_heuristic():
    frame = pd.DataFrame({"id": [1]})
    result = compare_by_join(frame, frame, on=["id"], keep_all=True)
    assert result.to_dict("records") == [{"id": 1, "__status__": "Added"}]


def test_join_preserves_existing_null_and_disjoint_column_classification():
    nulls = pd.DataFrame({"value": [None]})
    assert compare_by_join(nulls, nulls, keep_all=True).loc[0, "__status__"] == "Added"

    result = compare_by_join(pd.DataFrame({"a": [1]}), pd.DataFrame({"b": [2]}), keep_all=True)
    assert result.loc[0, "__status__"] == "Added"


def test_join_duplicate_indexes_produce_all_combinations():
    src = pd.DataFrame({"value": ["a", "b"]}, index=[1, 1])
    dst = pd.DataFrame({"value": ["a", "c"]}, index=[1, 1])
    result = compare_by_join(src, dst, keep_all=True)
    assert sorted(zip(result["value_old"], result["value_new"], result["__status__"])) == [
        ("a", "a", "Unchanged"), ("a", "c", "Changed"),
        ("b", "a", "Changed"), ("b", "c", "Changed"),
    ]
    assert len(compare_by_join(src, dst)) == 3
