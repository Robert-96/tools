import pandas as pd
import pytest

from src.compare import compare, compare_by_compare


def test_compare_keeps_full_shape_and_equal_values():
    src = pd.DataFrame({"value": ["old", "same"], "other": ["equal", "equal"]})
    dst = pd.DataFrame({"value": ["new", "same"], "other": ["equal", "equal"]})

    default = compare_by_compare(src, dst)
    expected_default = src.compare(dst, align_axis=0, keep_shape=False, keep_equal=False)
    pd.testing.assert_frame_equal(default, expected_default)
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


def test_compare_equal_and_empty_frames():
    frame = pd.DataFrame({"value": ["same", None]})
    assert compare_by_compare(frame, frame).empty
    kept = compare_by_compare(frame, frame, keep_all=True)
    assert kept.shape == (4, 1)
    assert kept.loc[(0, "self"), "value"] == "same"
    assert pd.isna(kept.loc[(1, "other"), "value"])
    empty = frame.iloc[:0]
    assert compare_by_compare(empty, empty).empty
    assert compare_by_compare(empty, empty, keep_all=True).empty


def test_compare_reports_null_difference_and_equal_nulls():
    src = pd.DataFrame({"value": [None, "old", None]})
    dst = pd.DataFrame({"value": ["new", None, None]})
    result = compare_by_compare(src, dst)
    assert result.index.tolist() == [(0, "self"), (0, "other"), (1, "self"), (1, "other")]
    assert pd.isna(result.loc[(0, "self"), "value"])
    assert result.loc[(0, "other"), "value"] == "new"
    assert result.loc[(1, "self"), "value"] == "old"
    assert pd.isna(result.loc[(1, "other"), "value"])


def test_compare_warns_if_on_is_passed():
    frame = pd.DataFrame({"value": [1]})
    with pytest.warns(UserWarning, match="'on' parameter"):
        result = compare_by_compare(frame, frame, on=["value"])
    assert result.empty


@pytest.mark.parametrize("dst", [
    pd.DataFrame({"other": [1]}),
    pd.DataFrame({"value": [1]}, index=[3]),
])
def test_compare_rejects_mismatched_labels(dst):
    with pytest.raises(ValueError, match="identically-labeled"):
        compare_by_compare(pd.DataFrame({"value": [1]}), dst)
