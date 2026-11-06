import pandas as pd

from src.compare import compare, compare_by_join


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


def test_join_duplicate_indexes_produce_all_combinations():
    src = pd.DataFrame({"value": ["a", "b"]}, index=[1, 1])
    dst = pd.DataFrame({"value": ["a", "c"]}, index=[1, 1])
    result = compare_by_join(src, dst, keep_all=True)
    assert sorted(zip(result["value_src"], result["value_dst"], result["__status__"])) == [
        ("a", "a", "Unchanged"), ("a", "c", "Changed"),
        ("b", "a", "Changed"), ("b", "c", "Changed"),
    ]
    assert len(compare_by_join(src, dst)) == 3


def test_join_on_does_not_match_right_column():
    src = pd.DataFrame({"id": [10], "value": ["old"]})
    dst = pd.DataFrame({"id": [10], "value": ["new"]})
    result = compare_by_join(src, dst, on=["id"], keep_all=True)
    assert sorted(result["__status__"].tolist()) == ["Added", "Removed"]
