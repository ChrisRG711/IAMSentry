"""Concurrent input/output workers implementation.

This module provides a two-level hierarchy of concurrent workers using
multiprocessing and multithreading for efficient I/O-bound operations.

Features:
- Configurable process and thread counts
- Queue size limits to prevent memory exhaustion
- Timeouts to prevent hanging workers
- Graceful shutdown handling
- Comprehensive error logging
"""

import multiprocessing
import os
import queue
import signal
import threading
import time
from typing import Any, Callable, Generator, Optional

from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

# Default configuration values
DEFAULT_QUEUE_SIZE = 1000
DEFAULT_WORKER_TIMEOUT = 300  # 5 minutes
DEFAULT_QUEUE_TIMEOUT = 60  # 1 minute

# Global shutdown flag for graceful termination
_shutdown_requested = threading.Event()


def run(
    input_func: Callable,
    output_func: Callable,
    processes: int = 0,
    threads: int = 0,
    log_tag: str = "",
    queue_size: int = DEFAULT_QUEUE_SIZE,
    worker_timeout: int = DEFAULT_WORKER_TIMEOUT,
    queue_timeout: int = DEFAULT_QUEUE_TIMEOUT,
) -> Generator[Any, None, None]:
    """Run concurrent input/output workers with specified functions.

    A two-level hierarchy of workers are created using both
    multiprocessing as well as multithreading. At first, ``processes``
    number of worker processes are created. Then within each process
    worker, ``threads`` number of worker threads are created. Thus, in
    total, ``processes * threads`` number of worker threads are created.

    Arguments:
        input_func: A callable which when called yields tuples. Each tuple
            must represent arguments to be passed to ``output_func``.
        output_func: A callable that can accept as arguments an unpacked
            tuple yielded by ``input_func``. When called, this callable
            must work on the arguments and return an output value.
            This callable must not return ``None`` for any input.
        processes: Number of worker processes to run. If unspecified or
            ``0`` or negative integer is specified, then the number
            returned by :func:`os.cpu_count` is used.
        threads: Number of worker threads to run in each process. If
            unspecified or ``0`` or negative integer is specified, then
            `5` multiplied by the number returned by :func:`os.cpu_count`
            is used.
        log_tag: String to include in every log message. This helps in
            differentiating between different workers invoked by different
            callers.
        queue_size: Maximum size of input/output queues. Prevents memory
            exhaustion with large datasets. Default: 1000.
        worker_timeout: Maximum time (seconds) for a worker to process a
            single item. Default: 300 (5 minutes).
        queue_timeout: Maximum time (seconds) to wait for queue operations.
            Default: 60 (1 minute).

    Yields:
        Each output value returned by ``output_func``.

    Raises:
        TimeoutError: If queue operations exceed the timeout.

    Example:
        >>> def get_projects():
        ...     for project in ['proj1', 'proj2']:
        ...         yield ('record', project)
        ...
        >>> def process_project(record_type, project):
        ...     yield {'project': project, 'status': 'ok'}
        ...
        >>> for record in run(get_projects, process_project, processes=2, threads=4):
        ...     print(record)
    """
    # Reset shutdown flag at start
    _shutdown_requested.clear()

    if processes <= 0:
        processes = os.cpu_count() or 4

    if threads <= 0:
        threads = (os.cpu_count() or 4) * 5

    if log_tag != "":
        log_tag += ": "

    _log.info(
        "%sStarting worker pool: %d processes, %d threads each, "
        "queue_size=%d, worker_timeout=%ds",
        log_tag,
        processes,
        threads,
        queue_size,
        worker_timeout,
    )

    # Create bounded queues to prevent memory exhaustion
    in_q = multiprocessing.Queue(maxsize=queue_size)
    out_q = multiprocessing.Queue(maxsize=queue_size)

    # Create process workers
    process_workers = []
    for i in range(processes):
        w = multiprocessing.Process(
            target=_process_worker,
            args=(in_q, out_q, threads, output_func, log_tag, worker_timeout),
            name=f"{log_tag}process-{i}",
        )
        w.start()
        process_workers.append(w)
        _log.debug("%sStarted process worker %d (pid=%d)", log_tag, i, w.pid)

    # Track statistics
    items_queued = 0
    start_time = time.time()

    try:
        # Get input data for thread workers to work on
        for args in input_func():
            if _shutdown_requested.is_set():
                _log.warning("%sShutdown requested, stopping input processing", log_tag)
                break
            try:
                in_q.put(args, timeout=queue_timeout)
                items_queued += 1
                if items_queued % 100 == 0:
                    _log.debug("%sQueued %d items", log_tag, items_queued)
            except Exception as e:
                _log.error(
                    "%sFailed to queue item (queue full?): %s: %s", log_tag, type(e).__name__, e
                )

        _log.info("%sFinished queuing %d items", log_tag, items_queued)

        # Tell each thread worker that there is no more input to work on
        for i in range(processes * threads):
            try:
                in_q.put(None, timeout=queue_timeout)
            except Exception as e:
                _log.error(
                    "%sFailed to send termination signal %d: %s: %s",
                    log_tag,
                    i,
                    type(e).__name__,
                    e,
                )

        # Consume output objects from thread workers and yield them
        yield from _get_output(out_q, processes, threads, log_tag, queue_timeout)

    except KeyboardInterrupt:
        _log.warning("%sKeyboard interrupt received, initiating graceful shutdown", log_tag)
        _shutdown_requested.set()
    finally:
        # Wait for process workers to terminate with timeout
        _log.debug("%sWaiting for process workers to terminate", log_tag)
        for i, w in enumerate(process_workers):
            w.join(timeout=worker_timeout)
            if w.is_alive():
                _log.warning(
                    "%sProcess worker %d (pid=%d) did not terminate, forcing", log_tag, i, w.pid
                )
                w.terminate()
                w.join(timeout=5)
                if w.is_alive():
                    _log.error("%sProcess worker %d still alive after terminate", log_tag, i)

        elapsed = time.time() - start_time
        _log.info(
            "%sWorker pool completed: processed %d items in %.2fs", log_tag, items_queued, elapsed
        )


def _process_worker(
    in_q: multiprocessing.Queue,
    out_q: multiprocessing.Queue,
    threads: int,
    output_func: Callable,
    log_tag: str,
    worker_timeout: int,
) -> None:
    """Process worker that spawns thread workers.

    Arguments:
        in_q: Input queue for work items.
        out_q: Output queue for results.
        threads: Number of thread workers to spawn.
        output_func: Function to process work items.
        log_tag: Tag for log messages.
        worker_timeout: Timeout for thread operations.
    """
    pid = os.getpid()
    _log.debug("%sProcess worker started (pid=%d)", log_tag, pid)

    thread_workers = []
    for i in range(threads):
        w = threading.Thread(
            target=_thread_worker,
            args=(in_q, out_q, output_func, log_tag, worker_timeout),
            name=f"{log_tag}thread-{i}",
            daemon=True,  # Daemon threads will be killed when main process exits
        )
        w.start()
        thread_workers.append(w)

    # Wait for thread workers to complete with timeout
    for i, w in enumerate(thread_workers):
        w.join(timeout=worker_timeout * 2)  # Allow extra time for thread completion
        if w.is_alive():
            _log.warning("%sThread worker %d in process %d did not complete", log_tag, i, pid)

    _log.debug("%sProcess worker completed (pid=%d)", log_tag, pid)


def _thread_worker(
    in_q: multiprocessing.Queue,
    out_q: multiprocessing.Queue,
    output_func: Callable,
    log_tag: str,
    worker_timeout: int,
) -> None:
    """Thread worker that processes items from input queue.

    Arguments:
        in_q: Input queue for work items.
        out_q: Output queue for results.
        output_func: Function to process work items.
        log_tag: Tag for log messages.
        worker_timeout: Timeout for processing each item.
    """
    thread_name = threading.current_thread().name
    items_processed = 0
    errors = 0

    while not _shutdown_requested.is_set():
        try:
            # Use timeout to allow checking shutdown flag periodically
            try:
                work = in_q.get(timeout=5)
            except Exception:
                # Queue.Empty or timeout - check shutdown and retry
                continue

            if work is None:
                out_q.put(None, timeout=worker_timeout)
                break

            # Process the work item
            start_time = time.time()
            try:
                for record in output_func(*work):
                    if _shutdown_requested.is_set():
                        break
                    out_q.put(record, timeout=worker_timeout)
                items_processed += 1

                elapsed = time.time() - start_time
                if elapsed > worker_timeout * 0.8:
                    _log.warning(
                        "%s[%s] Slow processing: %.2fs (threshold: %ds)",
                        log_tag,
                        thread_name,
                        elapsed,
                        worker_timeout,
                    )

            except Exception as e:
                errors += 1
                _log.exception(
                    "%s[%s] Failed to process work item; error: %s: %s",
                    log_tag,
                    thread_name,
                    type(e).__name__,
                    e,
                )
                # Continue processing other items despite errors

        except Exception as e:
            errors += 1
            _log.exception(
                "%s[%s] Thread worker error; error: %s: %s",
                log_tag,
                thread_name,
                type(e).__name__,
                e,
            )

    _log.debug(
        "%s[%s] Thread worker completed: processed=%d, errors=%d",
        log_tag,
        thread_name,
        items_processed,
        errors,
    )


def _get_output(
    out_q: multiprocessing.Queue, processes: int, threads: int, log_tag: str, queue_timeout: int
) -> Generator[Any, None, None]:
    """Get output from output queue and yield them.

    Arguments:
        out_q: Output queue to read from.
        processes: Number of process workers.
        threads: Number of thread workers per process.
        log_tag: Tag for log messages.
        queue_timeout: Timeout for queue operations.

    Yields:
        Output records from workers.
    """
    stopped_threads = 0
    expected_stops = processes * threads
    items_yielded = 0
    timeout_count = 0
    max_timeouts = 10  # Allow some timeouts before giving up

    _log.debug("%sWaiting for output from %d workers", log_tag, expected_stops)

    while stopped_threads < expected_stops:
        if _shutdown_requested.is_set():
            _log.warning("%sShutdown requested, stopping output collection", log_tag)
            break

        try:
            record = out_q.get(timeout=queue_timeout)
            timeout_count = 0  # Reset timeout counter on successful get

            if record is None:
                stopped_threads += 1
                _log.debug("%sWorker stopped (%d/%d)", log_tag, stopped_threads, expected_stops)
                continue

            items_yielded += 1
            yield record

        except Exception as e:
            timeout_count += 1
            if timeout_count >= max_timeouts:
                _log.error(
                    "%sToo many timeouts (%d) waiting for output, stopping", log_tag, timeout_count
                )
                break
            _log.debug("%sTimeout waiting for output (count=%d): %s", log_tag, timeout_count, e)

    _log.info("%sOutput collection complete: yielded %d items", log_tag, items_yielded)


def request_shutdown() -> None:
    """Request graceful shutdown of all workers.

    This sets the shutdown flag that workers check periodically.
    Workers will complete their current item before stopping.
    """
    _log.info("Shutdown requested for all workers")
    _shutdown_requested.set()


def is_shutdown_requested() -> bool:
    """Check if shutdown has been requested.

    Returns:
        True if shutdown was requested, False otherwise.
    """
    return _shutdown_requested.is_set()
