"""Isolated temporary files with guaranteed cleanup."""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)

_UPLOAD_ROOT = Path(tempfile.gettempdir()) / "trustmind_uploads"


def ensure_upload_root() -> Path:
    _UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    return _UPLOAD_ROOT


def safe_delete(path: Path | str | None) -> None:
    if not path:
        return
    p = Path(path)
    try:
        if p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    except OSError as exc:
        logger.warning("temp_cleanup_failed path=%s err=%s", p.name, type(exc).__name__)


@contextmanager
def temporary_upload_dir(prefix: str = "req_") -> Iterator[Path]:
    """
    Create an isolated directory under the upload root; always delete on exit.
    """
    root = ensure_upload_root()
    directory = root / f"{prefix}{uuid.uuid4().hex}"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        yield directory
    finally:
        safe_delete(directory)


@contextmanager
def temporary_file(
    *,
    suffix: str = "",
    prefix: str = "tm_",
    directory: Path | None = None,
) -> Iterator[Path]:
    """
    Yield a temp file path; delete the file (and optional parent dir) on exit.
    """
    parent = directory or ensure_upload_root()
    parent.mkdir(parents=True, exist_ok=True)
    path = parent / f"{prefix}{uuid.uuid4().hex}{suffix}"
    try:
        yield path
    finally:
        safe_delete(path)
