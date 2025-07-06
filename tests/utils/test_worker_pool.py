"""Tests for the generic worker_pool helper."""

from src.utils.worker_pool import map_parallel


def test_map_parallel_order_preserved():
    data = [1, 2, 3, 4]
    res = map_parallel(lambda x: x * x, data, preserve_order=True)
    assert res == [1, 4, 9, 16]


def test_map_parallel_no_order():
    data = [1, 2, 3, 4]
    res = map_parallel(lambda x: x * x, data, preserve_order=False)
    assert sorted(res) == [1, 4, 9, 16] 