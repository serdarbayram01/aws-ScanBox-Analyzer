"""TCP-connect latency probe — Python stdlib only.

Mirrors the behaviour of ist-LZ-TEST/benchsuite/internal/probes/latency.go:
open `samples` raw TCP connections to host:port, measure handshake RTT, return
min / p50 / p95 / max / stdev. No SSL, no payload, no auth — we only care
about the time the kernel takes to complete the three-way handshake.

Used by /awsref/api/region-matrix and /awsref/api/endpoints. NO AWS API
DEPENDENCY — works on any machine with outbound port-443 access."""

import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def probe_tcp(host: str, port: int = 443, samples: int = 5,
              timeout: float = 3.0) -> dict:
    """Open `samples` TCP sockets to host:port and time each handshake.

    Returns a dict with:
        reachable : bool
        min_ms, p50_ms, p95_ms, max_ms, stdev_ms : float (when reachable)
        error     : str (when not reachable)
        samples   : actual number of successful samples
    """
    rtts = []
    last_err = None
    for _ in range(samples):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            t0 = time.perf_counter()
            sock.connect((host, port))
            rtts.append((time.perf_counter() - t0) * 1000.0)
        except (socket.timeout, OSError) as exc:
            last_err = str(exc)
        finally:
            try:
                sock.close()
            except OSError:
                pass

    if not rtts:
        return {
            'reachable': False,
            'error':     last_err or 'connection failed',
            'samples':   0,
        }

    rtts_sorted = sorted(rtts)
    n = len(rtts_sorted)
    p50_idx = n // 2
    p95_idx = max(0, int(0.95 * n) - 1)
    return {
        'reachable': True,
        'samples':   n,
        'min_ms':    round(rtts_sorted[0], 2),
        'p50_ms':    round(rtts_sorted[p50_idx], 2),
        'p95_ms':    round(rtts_sorted[p95_idx], 2),
        'max_ms':    round(rtts_sorted[-1], 2),
        'stdev_ms':  round(statistics.pstdev(rtts_sorted), 2) if n > 1 else 0.0,
    }


def probe_many(targets: list, max_workers: int = 12, samples: int = 5,
               timeout: float = 3.0) -> list:
    """Fan-out across a list of targets via ThreadPoolExecutor — Python
    equivalent of the Go reference's goroutine fan-out.

    Each target is a dict that must contain at least `host`. Optional fields
    are preserved in the output: `port` (default 443), `label`, plus any
    free-form metadata callers want to carry through (e.g. `code`, `type`).
    """
    if not targets:
        return []

    def _probe_one(t):
        host = t.get('host') or t.get('endpoint') or ''
        port = int(t.get('port', 443))
        if not host:
            return {**t, 'reachable': False, 'error': 'no host'}
        result = probe_tcp(host, port, samples=samples, timeout=timeout)
        return {**t, **result}

    workers = max(1, min(max_workers, len(targets)))
    out = [None] * len(targets)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut_to_idx = {ex.submit(_probe_one, t): i for i, t in enumerate(targets)}
        for fut in as_completed(fut_to_idx):
            out[fut_to_idx[fut]] = fut.result()
    return out
