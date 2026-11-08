import importlib

import pandas as pd
import pytest


module = importlib.import_module("src.compare")


@pytest.mark.parametrize("method", ["merge", "join", "compare"])
def test_dispatcher_forwards_arguments_to_selected_method(monkeypatch, method):
    src = pd.DataFrame({"id": [1]})
    dst = pd.DataFrame({"id": [2]})
    expected = pd.DataFrame({"result": [42]})
    calls = []

    def fake_comparator(left, right, **kwargs):
        calls.append((left, right, kwargs))
        return expected

    monkeypatch.setitem(module.commands, method, fake_comparator)
    assert module.compare(src, dst, method=method, on=["id"], keep_all=True) is expected
    assert len(calls) == 1
    assert calls[0][0] is src and calls[0][1] is dst
    assert calls[0][2] == {"on": ["id"], "keep_all": True}


def test_dispatcher_defaults_to_merge(monkeypatch):
    frame = pd.DataFrame({"id": [1]})
    calls = []

    def fake_comparator(left, right, **kwargs):
        calls.append(kwargs)
        return left

    monkeypatch.setitem(module.commands, "merge", fake_comparator)
    assert module.compare(frame, frame) is frame
    assert calls == [{"on": None, "keep_all": False}]


def test_dispatcher_rejects_unsupported_method():
    frame = pd.DataFrame({"id": [1]})
    with pytest.raises(ValueError, match="Unsupported comparison method: invalid"):
        module.compare(frame, frame, method="invalid")


@pytest.mark.parametrize("method", ["merge", "join", "compare"])
def test_dispatcher_accepts_old_and_new_keywords(method):
    old = pd.DataFrame({"value": ["before"]})
    new = pd.DataFrame({"value": ["after"]})
    positional = module.compare(old, new, method=method, keep_all=True)
    keyword = module.compare(old=old, new=new, method=method, keep_all=True)
    pd.testing.assert_frame_equal(keyword, positional)


@pytest.mark.parametrize("comparator", [
    module.compare_by_merge,
    module.compare_by_join,
    module.compare_by_compare,
])
def test_comparator_accepts_old_and_new_keywords(comparator):
    old = pd.DataFrame({"value": ["before"]})
    new = pd.DataFrame({"value": ["after"]})
    positional = comparator(old, new, keep_all=True)
    keyword = comparator(old=old, new=new, keep_all=True)
    pd.testing.assert_frame_equal(keyword, positional)
