"""Utility functions for advanced regex operations with inclusion/exclusion of ranges and patterns."""

import re


def _ranges_overlap(
    start1,
    end1,
    start2,
    end2
):
    """Check if two ranges [start1, end1] and [start2, end2] overlap.

    Args:
        start1 (int): Start of the first range.
        end1 (int): End of the first range.
        start2 (int): Start of the second range.
        end2 (int): End of the second range.

    Returns:
        bool: True if the ranges overlap, False otherwise.

    Examples:
        >>> _ranges_overlap(1, 5, 4, 6)
        True
        >>> _ranges_overlap(1, 3, 4, 6)
        False
        >>> _ranges_overlap(1, 5, 5, 10)
        True
        >>> _ranges_overlap(1, 5, 6, 10)
        False
    """

    return start1 <= end2 and start2 <= end1


def find_within_ranges(
    string,
    pattern,
    included_ranges,
    count=0,
    flags=0
):
    """Find all occurrences of a pattern in a string, only within specified ranges.

    Args:
        string (str): The input string to search.
        pattern (str): The regex pattern to search for.
        included_ranges (list of tuples): List of (start, end) tuples specifying ranges to include for searching.
        count (int, optional): Maximum number of pattern occurrences to find. Defaults to 0 (find all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        list: A list of all matches found within the specified ranges.

    Examples:
        >>> find_within_ranges('foo baz foo', r'foo', [(7, 10)])
        ['foo']

        >>> find_within_ranges('abc 123 def 456', r'\\d+', [(4, 7)])
        ['123']

        >>> find_within_ranges('hello world', r'\\w+', [(0, 5)])
        ['hello']

        >>> find_within_ranges('hello world', r'\\w+', [(0, 5), (6, 11)])
        ['hello', 'world']

        >>> find_within_ranges('hello world', r'\\w+', [(0, 5)], count=1)
        ['hello']

        >>> find_within_ranges('hello world', r'\\w+', [(0, 5)], flags=re.IGNORECASE)
        ['hello']
    """

    matches = []
    found = 0

    for match in re.finditer(pattern, string, flags=flags):
        if count and found >= count:
            break

        start, end = match.span()

        for in_start, in_end in included_ranges:
            if _ranges_overlap(start, end - 1, in_start, in_end - 1):
                matches.append(match.group(0))
                found += 1
                break

    return matches


def find_with_excluded_ranges(
    string,
    pattern,
    excluded_ranges,
    count=0,
    flags=0
):
    """Find all occurrences of a pattern in a string, excluding specified ranges.

    Args:
        string (str): The input string to search.
        pattern (str): The regex pattern to search for.
        excluded_ranges (list of tuples): List of (start, end) tuples specifying ranges to exclude from searching.
        count (int, optional): Maximum number of pattern occurrences to find. Defaults to 0 (find all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        list: A list of all matches found outside the excluded ranges.

    Examples:
        >>> find_with_excluded_ranges('foo baz foo', r'foo', [(7, 10)])
        ['foo']

        >>> find_with_excluded_ranges('abc 123 def 456', r'\\d+', [(4, 7)])
        ['456']

        >>> find_with_excluded_ranges('hello world', r'\\w+', [(0, 5)])
        ['world']

        >>> find_with_excluded_ranges('hello world', r'\\w+', [(0, 5), (6, 11)])
        []

        >>> find_with_excluded_ranges('foo bar foo', r'\\w+', [(0, 4)], count=1)
        ['bar']

        >>> find_with_excluded_ranges('world World WORLD', r'\\w+', [(0, 5)], flags=re.IGNORECASE)
        ['World', 'WORLD']
    """

    matches = []
    found = 0

    for match in re.finditer(pattern, string, flags=flags):
        if count and found >= count:
            break

        start, end = match.span()

        overlap = False
        for ex_start, ex_end in excluded_ranges:
            if _ranges_overlap(start, end - 1, ex_start, ex_end - 1):
                overlap = True
                break

        if not overlap:
            matches.append(match.group(0))
            found += 1

    return matches


def find_within_patterns(
    string,
    pattern,
    included_patterns,
    count=0,
    flags=0
):
    """Find all occurrences of a pattern in a string, only within specified patterns.

    Args:
        string (str): The input string to search.
        pattern (str): The regex pattern to search for.
        included_patterns (list of str): List of regex patterns specifying matches to include for searching.
        count (int, optional): Maximum number of pattern occurrences to find. Defaults to 0 (find all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        list: A list of all matches found within the included patterns.

    Examples:
        >>> find_within_patterns('foo bar "foo"', r'foo', [r'"[^"]*"'])
        ['foo']

        >>> find_within_patterns('abc 123 def "456"', r'\\d+', [r'"[^"]*"'])
        ['456']

        >>> find_within_patterns('hello world (goodbye)', r'\\w+', [r'\\(.*?\\)'])
        ['goodbye']

        >>> find_within_patterns('foo bar (foo) [baz]', r'\\w+', [r'\\(.*?\\)', r'\\[.*?\\]'])
        ['foo', 'baz']

        >>> find_within_patterns('foo bar (foo) [baz]', r'\\w+', [r'\\(.*?\\)', r'\\[.*?\\]'], count=1)
        ['foo']

        >>> find_within_patterns('world worldwide WORLD WORLDWIDE', r'\\w+', [r'worldwide'], flags=re.IGNORECASE)
        ['worldwide', 'WORLDWIDE']

    """

    matches = []
    found = 0

    for inc_pattern in included_patterns:
        for inc_match in re.finditer(inc_pattern, string, flags=flags):
            start, end = inc_match.span()
            for match in re.finditer(pattern, string[start:end], flags=flags):
                if count and found >= count:
                    break
                matches.append(match.group(0))
                found += 1

    return matches


def find_with_excluded_patterns(
    string,
    pattern,
    excluded_patterns,
    count=0,
    flags=0
):
    """Find all occurrences of a pattern in a string, excluding matches within specified patterns.

    Args:
        string (str): The input string to search.
        pattern (str): The regex pattern to search for.
        excluded_patterns (list of str): List of regex patterns specifying matches to exclude from searching.
        count (int, optional): Maximum number of pattern occurrences to find. Defaults to 0 (find all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        list: A list of all matches found outside the excluded patterns.

    Examples:
        >>> find_with_excluded_patterns('foo foot foo', r'foo', [r'foot'])
        ['foo', 'foo']

        >>> find_with_excluded_patterns('abc 123 def 456', r'\\d+', [r'123'])
        ['456']

        >>> find_with_excluded_patterns('abc 123 def 1234', r'\\d+', [r'1234'])
        ['123']

        >>> find_with_excluded_patterns('hello world', r'\\w+', [r'hello'])
        ['world']

        >>> find_with_excluded_patterns('foo bar foo bar', r'\\w+', [r'foo'], count=1)
        ['bar']

        >>> find_with_excluded_patterns('world worldwide WORLD WORLDWIDE', r'\\w+', [r'worldwide'], flags=re.IGNORECASE)
        ['world', 'WORLD']
    """

    matches = []
    found = 0

    excluded_spans = []
    for ex_pattern in excluded_patterns:
        for ex_match in re.finditer(ex_pattern, string, flags=flags):
            excluded_spans.append(ex_match.span())

    for match in re.finditer(pattern, string, flags=flags):
        if count and found >= count:
            break

        start, end = match.span()

        overlap = False
        for ex_start, ex_end in excluded_spans:
            if _ranges_overlap(start, end - 1, ex_start, ex_end - 1):
                overlap = True
                break

        if not overlap:
            matches.append(match.group(0))
            found += 1

    return matches


def replace_within_ranges(
    string,
    pattern,
    replacement,
    included_ranges,
    count=0,
    flags=0,
):
    """Replace occurrences of a pattern in a string, only within specified ranges.

    Args:
        string (str): The input string to perform replacements on.
        pattern (str): The regex pattern to search for.
        replacement (str): The string to replace the matched patterns with.
        included_ranges (list of tuples): List of (start, end) tuples specifying ranges to include for replacement.
        count (int, optional): Maximum number of pattern occurrences to replace. Defaults to 0 (replace all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        str: The modified string with replacements made only within the included ranges.

    Examples:
        >>> replace_within_ranges('foo baz foo', r'foo', 'bar', [(4, 7)])
        'foo baz foo'

        >>> replace_within_ranges('foo baz foo', r'foo', 'bar', [(0, 4)])
        'bar baz foo'

        >>> replace_within_ranges('abc 123 def 456', r'\\d+', 'NUM', [(4, 7)])
        'abc NUM def 456'

        >>> replace_within_ranges('hello world', r'\\w+', 'WORD', [(0, 5)])
        'WORD world'

        >>> replace_within_ranges('hello world', r'\\w+', 'WORD', [(0, 5), (6, 11)])
        'WORD WORD'

        >>> replace_within_ranges('hello world', r'\\w+', 'WORD', [(0, 5)], count=1)
        'WORD world'

        >>> replace_within_ranges('hello world', r'\\w+', 'WORD', [(0, 5)], flags=re.IGNORECASE)
        'WORD world'
    """

    def replacement_function(match):
        start, end = match.span()
        for in_start, in_end in included_ranges:
            if _ranges_overlap(start, end - 1, in_start, in_end - 1):
                return replacement
        return match.group(0)

    return re.sub(pattern, replacement_function, string, count=count, flags=flags)


def replace_with_excluded_ranges(
    string,
    pattern,
    replacement,
    excluded_ranges,
    count=0,
    flags=0,
):
    """Replace occurrences of a pattern in a string, excluding specified ranges.

    Args:
        string (str): The input string to perform replacements on.
        pattern (str): The regex pattern to search for.
        replacement (str): The string to replace the matched patterns with.
        excluded_ranges (list of tuples): List of (start, end) tuples specifying ranges to exclude from replacement.
        count (int, optional): Maximum number of pattern occurrences to replace. Defaults to 0 (replace all).
        flags (int, optional): Regex flags to use. Defaults to 0.

    Returns:
        str: The modified string with replacements made outside the excluded ranges.

    Examples:
        >>> replace_with_excluded_ranges('foo baz foo', r'foo', 'bar', [(7, 10)])
        'bar baz foo'

        >>> replace_with_excluded_ranges('abc 123 def 456', r'\\d+', 'NUM', [(4, 7)])
        'abc 123 def NUM'

        >>> replace_with_excluded_ranges('hello world', r'\\w+', 'WORD', [(0, 5)])
        'hello WORD'

        >>> replace_with_excluded_ranges('hello world', r'\\w+', 'WORD', [(0, 5), (6, 11)])
        'hello world'

        >>> replace_with_excluded_ranges('foo bar foo', r'\\w+', 'WORD', [(0, 4)], count=1)
        'foo WORD foo'

        >>> replace_with_excluded_ranges('world world WORLD', r'\\w+', 'WORD', [(0, 5)], flags=re.IGNORECASE)
        'world WORD WORD'

    """

    replaced = 0

    def replacement_function(match):
        nonlocal replaced

        if count and replaced >= count:
            return match.group(0)

        start, end = match.span()
        for ex_start, ex_end in excluded_ranges:
            if _ranges_overlap(start, end - 1, ex_start, ex_end - 1):
                return match.group(0)

        replaced += 1
        return replacement

    return re.sub(pattern, replacement_function, string, flags=flags)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
