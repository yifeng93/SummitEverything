"""Internal-app backend entry point with parent-death cleanup."""

from __future__ import annotations

import os
import signal
import sys
from threading import Event, Thread
from typing import BinaryIO

import uvicorn

from summit_everything.api.app import app


def watch_parent_pipe(reader: BinaryIO, exited: Event) -> None:
    """Mark the native owner as gone when it closes the inherited pipe."""
    reader.read(1)
    exited.set()


def main() -> None:
    parent_exited = Event()
    Thread(target=watch_parent_pipe, args=(sys.stdin.buffer, parent_exited), daemon=True).start()

    def terminate_on_parent_exit() -> None:
        parent_exited.wait()
        os.kill(os.getpid(), signal.SIGTERM)

    Thread(target=terminate_on_parent_exit, daemon=True).start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ["SUMMIT_API_PORT"]),
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
