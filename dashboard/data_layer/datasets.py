"""Các bộ dữ liệu thật để chọn trên giao diện.

Mỗi bộ là một thư mục chứa các bảng (<tên bảng>.csv hoặc .parquet) và, nếu có, images.zip của chính
bộ đó. Bộ không có images.zip thì dùng ảnh của bộ đáp án.
- Bộ mặc định (tên rỗng): thư mục REAL_DIR, như trước khi có nhiều bộ.
- Bộ trên máy: mỗi thư mục con của DATASETS_DIR.
- Bộ trên Vercel Blob: mỗi thư mục con của BLOB_PREFIX trong store đã nối với project. API tải bộ
  đang chọn về thư mục tạm và chỉ tải lại file đã đổi. Mỗi lần liệt kê Blob tính một thao tác, nên
  danh sách chỉ hỏi lại sau REFRESH_SECONDS: tải bộ mới lên thì vài phút sau mới thấy.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path

import settings as S

REFRESH_SECONDS = 300
_CACHE_DIR = Path(tempfile.gettempdir()) / "m22-datasets"
_BLOB_ENV = ("BLOB_STORE_ID", "BLOB_READ_WRITE_TOKEN", "VERCEL_BLOB_READ_WRITE_TOKEN")

_lock = threading.Lock()
_remote: dict[str, dict] = {}  # tên bộ -> {tên file: ListBlob}
_listed_at = float("-inf")
_pulled: dict[str, dict[str, str]] = {}  # tên bộ -> {tên file: etag của bản đã tải}


class SourceError(RuntimeError):
    """Không đọc được Vercel Blob: thiếu quyền, mất mạng, store bị khoá..."""


def blob_enabled() -> bool:
    """Project đã nối với một Blob store (Vercel thêm các biến này khi nối) hoặc có token đọc ghi."""
    return any(os.environ.get(key) for key in _BLOB_ENV)


def _local() -> list[str]:
    if not S.DATASETS_DIR.is_dir():
        return []
    return [p.name for p in S.DATASETS_DIR.iterdir() if p.is_dir() and not p.name.startswith(".")]


def _remote_files() -> dict[str, dict]:
    """Các file trên Blob, theo bộ; chỉ lấy file nằm thẳng trong thư mục của bộ. Gọi khi giữ `_lock`."""
    global _remote, _listed_at
    if not blob_enabled():
        return {}
    if time.monotonic() - _listed_at < REFRESH_SECONDS:
        return _remote
    from vercel.blob import sync as blob

    found: dict[str, dict] = {}
    try:
        for item in blob.query_blobs(prefix=S.BLOB_PREFIX):
            name, _, file = item.pathname.removeprefix(S.BLOB_PREFIX).partition("/")
            if name and file and "/" not in file:
                found.setdefault(name, {})[file] = item
    except blob.BlobError as error:
        raise SourceError(f"Không liệt kê được các bộ dữ liệu trên Vercel Blob: {error}") from error
    _remote, _listed_at = found, time.monotonic()
    return found


def _pull(name: str, files: dict) -> Path:
    """Đồng bộ bộ `name` từ Blob về thư mục tạm. Gọi khi giữ `_lock`."""
    from vercel.blob import sync as blob

    dest = _CACHE_DIR / name
    dest.mkdir(parents=True, exist_ok=True)
    have = _pulled.setdefault(name, {})
    try:
        for file, item in files.items():
            if have.get(file) == item.etag and (dest / file).exists():
                continue
            part = dest / f"{file}.part"
            with blob.stream_blob(item.url, access=S.BLOB_ACCESS) as download, part.open("wb") as out:
                for chunk in download:
                    out.write(chunk)
            part.replace(dest / file)
            have[file] = item.etag
    except blob.BlobError as error:
        raise SourceError(f"Không tải được bộ `{name}` từ Vercel Blob: {error}") from error
    for file in set(have) - set(files):  # đã xoá trên Blob
        (dest / file).unlink(missing_ok=True)
        del have[file]
    return dest


def names() -> list[str]:
    """Tên các bộ chọn được, không gồm bộ mặc định."""
    with _lock:
        return sorted(set(_local()) | set(_remote_files()))


def folder(name: str) -> Path:
    """Thư mục trên máy chứa bộ `name`; tên rỗng là bộ mặc định. KeyError nếu không có bộ này."""
    if not name:
        return S.REAL_DIR
    if name in _local():
        return S.DATASETS_DIR / name
    with _lock:
        files = _remote_files().get(name)
        if files is None:
            raise KeyError(name)
        return _pull(name, files)


def _shown(path: Path) -> str:
    return path.relative_to(S.PROJECT_DIR).as_posix() if S.PROJECT_DIR in path.parents else str(path)


def where(name: str) -> str:
    """Bộ `name` nằm ở đâu, để hiện trên trang Nguồn dữ liệu."""
    if not name:
        return _shown(S.REAL_DIR)
    if name in _local():
        return _shown(S.DATASETS_DIR / name)
    return f"Vercel Blob · {S.BLOB_PREFIX}{name}"
