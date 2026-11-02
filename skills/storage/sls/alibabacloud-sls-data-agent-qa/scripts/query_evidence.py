"""Atomic, non-overwriting local log-query records, separate from stdout."""

import os
import tempfile
from pathlib import Path

from slsmodel.encoding import dumps


class LogQueryRecord:
    def __init__(self, path):
        self.path = Path(path).absolute() if path else None
        self.temp = None

    def __enter__(self):
        if self.path is not None:
            if os.path.lexists(self.path):
                raise FileExistsError("Query record already exists: " + str(self.path))
            self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd, self.temp = tempfile.mkstemp(prefix=".sls-query-", suffix=".tmp", dir=self.path.parent)
            os.close(fd)
        return self

    def commit(self, request, result):
        if self.temp is None:
            return
        with open(self.temp, "w", encoding="utf-8") as stream:
            stream.write(dumps({**result, "request": request}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard linking publishes a whole file and fails if the target now exists.
        os.link(self.temp, self.path)

    def __exit__(self, *_):
        if self.temp is not None:
            os.unlink(self.temp)
