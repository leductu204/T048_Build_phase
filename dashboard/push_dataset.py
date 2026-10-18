"""Đưa một bộ dữ liệu thật lên Vercel Blob để chọn trên dashboard.

Chạy từ thư mục gốc của project:
    python dashboard/push_dataset.py <tên bộ> <thư mục>

Thư mục chứa các bảng (<tên bảng>.csv hoặc .parquet) và, nếu có, images.zip của bộ đó; file khác bị bỏ
qua. Chạy lại với cùng tên để cập nhật: file trong thư mục ghi đè bản trên Blob, file không còn trong
thư mục bị xoá khỏi Blob. Dashboard thấy thay đổi sau tối đa vài phút (datasets.REFRESH_SECONDS).

Cần biến môi trường BLOB_READ_WRITE_TOKEN của store (Vercel > Storage > store > tab .env.local).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings as S  # noqa: E402
from data_layer import schema  # noqa: E402

ACCEPTED = {f"{table}{ext}" for table in schema.TABLES for ext in (".csv", ".parquet")} | {"images.zip"}
CACHE_SECONDS = 60  # bản cũ chỉ còn trong cache CDN tối đa bấy nhiêu giây sau khi ghi đè


def main() -> None:
    parser = argparse.ArgumentParser(description="Đưa một bộ dữ liệu lên Vercel Blob.")
    parser.add_argument("name", help="tên bộ, hiện trong ô chọn trên dashboard; chỉ gồm chữ, số, . _ -")
    parser.add_argument("folder", type=Path, help="thư mục chứa các bảng và images.zip")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.name):
        sys.exit(f"Tên bộ không hợp lệ: {args.name!r}. Chỉ dùng chữ, số, dấu chấm, gạch dưới, gạch ngang.")
    if not args.folder.is_dir():
        sys.exit(f"Không thấy thư mục {args.folder}.")
    files = sorted(f for f in args.folder.iterdir() if f.is_file() and f.name in ACCEPTED)
    if not any(f.name != "images.zip" for f in files):
        sys.exit(f"{args.folder} không có bảng nào (<tên bảng>.csv hoặc .parquet).")

    from vercel.blob import sync as blob

    prefix = f"{S.BLOB_PREFIX}{args.name}/"
    for f in files:
        with f.open("rb") as body:
            blob.put_blob(prefix + f.name, body, access=S.BLOB_ACCESS, content_length=f.stat().st_size,
                          allow_overwrite=True, cache_control_max_age=CACHE_SECONDS)
        print(f"Đã tải lên {prefix}{f.name}")

    kept = {prefix + f.name for f in files}
    stale = [item.pathname for item in blob.query_blobs(prefix=prefix) if item.pathname not in kept]
    if stale:
        blob.delete_blob(stale)
        print("Đã xoá khỏi Blob:", ", ".join(stale))


if __name__ == "__main__":
    main()
