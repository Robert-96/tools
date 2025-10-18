import pytest

from src.regexutils import (
    _do_ranges_overlap,
    find_within_ranges,
    find_strings_within_ranges,
    find_with_excluded_ranges,
)


@pytest.mark.parametrize(
    "start1, end1, start2, end2, expected",
    [
        (0, 5, 3, 7, True),  # Overlapping ranges
        (2, 6, 0, 3, True),   # Overlapping ranges
        (0, 2, 3, 5, False),  # Non-overlapping ranges
        (3, 5, 0, 2, False),  # Non-overlapping ranges
        (4, 6, 1, 5, True),  # Touching at the end
        (5, 10, 9, 15, True),  # Touching at the start
        (0, 10, 5, 15, True),  # One range inside another
    ]
)
def test_ranges_overlap(start1, end1, start2, end2, expected):
    assert _do_ranges_overlap(start1, end1, start2, end2) == expected


@pytest.mark.parametrize(
    "text, pattern, ranges, expected_spans",
    [
        (
            "The quick brown fox jumps over the lazy dog",
            r'\b\w{3}\b',  # Matches 3-letter words
            [(0, 10), (20, 40)],  # Ranges to search within
            [(0, 3), (31, 34)]
        ),
        (
            "Hello world, this is a test string",
            r'\b\w{4}\b',  # Matches 4-letter words
            [(0, 15), (20, 35)],
            [(13, 17), (23, 27)]
        ),
        (
            "Python is great for programming",
            r'\b[Pp]\w+\b',  # Matches words starting with P or p
            [(0, 20)],
            [(0, 6)]
        ),
        (
            "No matches here",
            r'\d+',  # Matches digits
            [(0, 15)],
            []
        ),
    ]
)
def test_find_within_ranges(text, pattern, ranges, expected_spans):
    matches = find_within_ranges(text, pattern, ranges)
    assert [match.span() for match in matches] == expected_spans


@pytest.mark.parametrize(
    "text, pattern, ranges, expected_matches",
    [
        (
            "The quick brown fox jumps over the lazy dog",
            r'\b\w{3}\b',  # Matches 3-letter words
            [(0, 10), (20, 40)],  # Ranges to search within
            ['The', 'the']
        ),
        (
            "Hello world, this is a test string",
            r'\b\w{4}\b',  # Matches 4-letter words
            [(0, 15), (20, 35)],
            ['this', 'test']
        ),
        (
            "Python is great for programming",
            r'\b[Pp]\w+\b',  # Matches words starting with P or p
            [(0, 20)],
            ['Python']
        ),
        (
            "No matches here",
            r'\d+',  # Matches digits
            [(0, 15)],
            []
        ),
    ]
)
def test_find_strings_within_ranges(text, pattern, ranges, expected_matches):
    matches = find_strings_within_ranges(text, pattern, ranges)
    assert matches == expected_matches


@pytest.mark.parametrize(
    "text, pattern, excluded_ranges, expected_spans",
    [
        (
            "The quick brown fox jumps over the lazy dog",
            r'\b\w{3}\b',  # Matches 3-letter words
            [(0, 10), (20, 40)],  # Ranges to exclude
            [(16, 19), (40, 43)]
        ),
        (
            "Hello world, this is a test string",
            r'\b\w{4}\b',  # Matches 4-letter words
            [(0, 15), (20, 35)],
            []
        ),
        (
            "Python is great for programming",
            r'\b[Pp]\w+\b',  # Matches words starting with P or p
            [(0, 20)],
            [(20, 31)]
        ),
        (
            "No matches here",
            r'\d+',  # Matches digits
            [(0, 15)],
            []
        ),
    ]
)
def test_find_with_excluded_ranges(text, pattern, excluded_ranges, expected_spans):
    matches = find_with_excluded_ranges(text, pattern, excluded_ranges)
    assert [match.span() for match in matches] == expected_spans
