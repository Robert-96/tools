import pytest

from src.regexutils import _do_ranges_overlap


@pytest.mark.parametrize(
    "start1, end1, start2, end2, expected",
    [
        (0, 5, 3, 7, True), # Overlapping ranges
        (2, 6, 0, 3, True),  # Overlapping ranges
        (0, 2, 3, 5, False), # Non-overlapping ranges
        (3, 5, 0, 2, False), # Non-overlapping ranges
        (4, 6, 1, 5, True), # Touching at the end
        (5, 10, 9, 15, True), # Touching at the start
        (0, 10, 5, 15, True), # One range inside another
    ]
)
def test_ranges_overlap(start1, end1, start2, end2, expected):
    assert _do_ranges_overlap(start1, end1, start2, end2) == expected
