"""Generic worker-pool helper for running CPU/light I/O tasks in parallel.

Intentionally lightweight – wraps ThreadPoolExecutor and captures exceptions so
callers receive results in the same order as input items (à la built-in map).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable, Iterable, List, TypeVar, Tuple

T = TypeVar("T")
R = TypeVar("R")


def map_parallel(
    func: Callable[[T], R],
    items: Iterable[T],
    *,
    max_workers: int = 8,
    preserve_order: bool = True,
) -> List[R]:
    """Run *func* over *items* using a worker pool.

    Args:
        func: Callable executed for each item.
        items: Iterable of inputs.
        max_workers: Limit of concurrent threads (default 8).
        preserve_order: If True, results are returned in the same order as
            *items*. Otherwise, results return as soon as each task finishes.

    Returns:
        List of results, possibly containing exceptions raised by *func*.
    """
    if preserve_order:
        # Submit tasks preserving index for stable ordering.
        futures: List[Tuple[int, Future[R]]]=[]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for idx, item in enumerate(items):
                futures.append((idx, executor.submit(func, item)))

        # Collect in order of original indices.
        results: List[R] = [None] * len(futures)  # type: ignore[list-item]
        for idx, fut in futures:
            try:
                results[idx] = fut.result()
            except Exception as exc:  # pragma: no cover
                results[idx] = exc  # type: ignore[assignment]
        return results
    else:
        # Return as-completed order.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(func, item): item for item in items}
            results: List[R] = []
            for future in as_completed(future_to_item):
                try:
                    results.append(future.result())
                except Exception as exc:  # pragma: no cover
                    results.append(exc)  # type: ignore[arg-type]
            return results 