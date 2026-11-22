"""Health probes and payload-free worker events."""

import logging
import signal
import sys
import time
from pathlib import Path
from threading import Event
from urllib.request import Request, urlopen

from app.settings import deployed, deployment_host

HEARTBEAT = Path("/tmp/openbook-worker.ready")


def heartbeat() -> None:
    if deployed():
        HEARTBEAT.touch()


def shutdown_event() -> Event:
    stopped = Event()

    def stop(signum, frame):
        stopped.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    return stopped


def worker_logger(name: str) -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='{"level":"%(levelname)s","event":"%(message)s"}',
    )
    logger = logging.getLogger(name)
    logger.info("worker_started")
    return logger


if __name__ == "__main__":
    if sys.argv[1] == "api":
        with urlopen(
            Request(
                "http://127.0.0.1:8000/api/health",
                headers={"Host": deployment_host()},
            ),
            timeout=3,
        ) as response:
            sys.exit(response.status != 200)
    sys.exit(not HEARTBEAT.exists() or time.time() - HEARTBEAT.stat().st_mtime > 60)
