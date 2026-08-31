"""Cross-process workspace locks and observable command lifecycle records."""

from __future__ import annotations

from contextvars import ContextVar
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path


class WorkspaceBusy(RuntimeError):
    pass


class WorkspaceLock:
    """OS lock released on process exit; persistent lock files are not stale locks."""

    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        key = hashlib.sha256(str(self.directory).casefold().encode() if os.name == "nt" else str(self.directory).encode()).hexdigest()
        self.path = self.directory.parent / ".sxs-locks" / f"{key}.lock"
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        if stream.seek(0, 2) == 0:
            stream.write(b"\n")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise WorkspaceBusy(f"Workspace is in use: {self.directory}") from exc
        self.stream = stream
        return self

    def __exit__(self, *args):
        if self.stream:
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
            self.stream.close()


ACTIVE_OPERATION = ContextVar("sxs_operation", default=None)


class Operation:
    def __init__(self, command: str):
        self.path = None
        self.lock = None
        self.contexts = ExitStack()
        self.record = {"schema_version": 1, "command": command, "pid": os.getpid(),
                       "status": "running", "started_at_utc": datetime.now(timezone.utc).isoformat()}

    def register(self, directory: Path, *, legacy=False):
        if not legacy:
            self.lock = WorkspaceLock(directory)
            self.lock.__enter__()
        self.path = (directory / (".sxs-state/operation_latest.json" if legacy else "operation.json")).resolve()
        self.flush()

    def flush(self):
        if self.path is not None:
            from src.provenance import atomic_json
            self.record["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            atomic_json(self.path, self.record)

    def finish(self, status: str, code: int, error: str | None = None):
        self.record.update(status=status, exit_code=code, finished_at_utc=datetime.now(timezone.utc).isoformat())
        if error:
            self.record["error"] = error
        try:
            self.flush()
        except OSError as exc:
            import sys
            print(f"SXS could not save final operation status: {exc}", file=sys.stderr)

    def close(self):
        try:
            if self.lock:
                self.lock.__exit__(None, None, None)
                self.lock = None
        finally:
            self.contexts.close()


def register_output(directory: Path):
    operation = ACTIVE_OPERATION.get()
    if operation:
        operation.register(directory)


def progress(stage: str, completed: int, total: int):
    operation = ACTIVE_OPERATION.get()
    if operation:
        operation.record["progress"] = {"stage": stage, "completed": completed, "total": total}
        operation.flush()
