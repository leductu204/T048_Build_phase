"""Một cửa nạp dữ liệu cho dashboard.

Hai chế độ, không bao giờ trộn số thật với số giả:
- Thật: có ít nhất một file trong thư mục bảng thật. Bảng nào chưa có hoặc bị từ chối thì
  để trống, các trang ghi "chưa có dữ liệu" chứ không lấy số giả lấp vào.
- Giả: chưa có file thật nào, hoặc người xem bật "Xem bằng dữ liệu giả".

Module này không phụ thuộc giao diện: bản Streamlit và API cùng gọi `load()`.
Bảng trả về được dùng chung giữa các lượt gọi, nên các trang chỉ đọc, không sửa tại chỗ.
"""
from __future__ import annotations

import io
import threading
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

import settings as S
from data_layer import codec, mock, schema

REAL, MOCK, ABSENT = "Thật", "Giả", "Chưa có"
DEMO_KEY = "demo_mode"  # khoá session_state của công tắc "Xem bằng dữ liệu giả" trên bản Streamlit

_lock = threading.Lock()  # dựng dữ liệu giả mất vài giây; các request đến cùng lúc chờ một lần dựng


@dataclass
class Tables:
    mode: str  # REAL hoặc MOCK
    frames: dict[str, pd.DataFrame]  # chỉ gồm bảng dùng được
    origin: dict[str, str]  # tên bảng -> REAL, MOCK hoặc ABSENT
    problems: dict[str, str]  # tên bảng -> vì sao chưa dùng được
    missing: dict[str, list[str]]  # tên bảng -> cột tuỳ chọn chưa có
    has_real_files: bool = False
    images: Path = S.IMAGES_ZIP  # file zip chứa ảnh của các issue

    def __getitem__(self, name: str) -> pd.DataFrame:
        return self.frames[name]

    def available(self, name: str) -> bool:
        return name in self.frames

    def has(self, name: str, *cols: str) -> bool:
        """Bảng dùng được và có đủ các cột tuỳ chọn này."""
        return name in self.frames and not set(cols) & set(self.missing.get(name, ()))

    def gaps(self, **needs: list[str]) -> list[str]:
        """Những gì còn thiếu cho một phần giao diện, mỗi dòng một câu; rỗng nghĩa là đủ.

        `needs`: tên bảng -> các cột tuỳ chọn cần có (danh sách rỗng nếu chỉ cần bảng tồn tại).
        """
        out = []
        for table, cols in needs.items():
            spec = schema.TABLES[table]
            if not self.available(table):
                out.append(f"Chưa dùng được bảng `{table}` ({spec['stage']}): {self.problems.get(table, 'không rõ')}.")
                continue
            lacking = [c for c in cols if c in self.missing.get(table, ())]
            if lacking:
                listed = ", ".join(f"`{c}` ({spec['optional'][c]})" for c in lacking)
                out.append(f"Bảng `{table}` chưa có cột {listed}.")
        return out

    def badge(self, used: list[str]) -> tuple[str, str, str | None]:
        """Huy hiệu nguồn dữ liệu của một trang: (loại, chữ, giải thích). Loại là mock, partial hoặc real."""
        if self.mode == MOCK:
            return "mock", "Dữ liệu giả", "Mọi con số trên trang này là số tự sinh, không phải kết quả đo."
        absent = [t for t in used if not self.available(t)]
        if absent:
            return "partial", f"Dữ liệu thật · thiếu {len(absent)}/{len(used)} bảng", "Bảng chưa có: " + ", ".join(absent)
        return "real", "Dữ liệu thật", None

    def annotator_names(self) -> list[str]:
        if self.available("annotators"):
            return list(self["annotators"]["annotator"])
        names: set[str] = set()
        for table, col in (("issues", "annotator"), ("pair_agreement", "annotator_a"), ("patches", "annotator")):
            if self.available(table):
                names |= set(self[table][col].dropna())
        return sorted(names)


def real_path(name: str, folder: Path | None = None) -> Path | None:
    for ext in (".parquet", ".csv"):
        path = (folder or S.REAL_DIR) / f"{name}{ext}"
        if path.exists():
            return path
    return None


def _code_version() -> tuple[float, ...]:
    """Đổi khi bộ sinh, hợp đồng hoặc bảng mã đổi, để bộ nhớ đệm không giữ kết quả cũ."""
    return tuple(Path(module.__file__).stat().st_mtime for module in (S, schema, codec, mock))


@lru_cache(maxsize=2)
def _mock_tables(version: tuple) -> dict[str, pd.DataFrame]:
    return mock.build_all()


@lru_cache(maxsize=32)
def _read_real(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)


@lru_cache(maxsize=4)
def _assemble(mode: str, files: tuple, version: tuple, has_real_files: bool, images: Path) -> Tables:
    if mode == REAL:
        raw = {name: _read_real(path, mtime) for name, path, mtime in files}
    else:
        raw = _mock_tables(version + (files[0][2],))

    frames, origin, problems, missing = {}, {}, {}, {}
    for name in schema.TABLES:
        if name not in raw:
            origin[name], problems[name] = ABSENT, f"chưa có file {name}.csv"
            continue
        df, lacking, problem = codec.decode(name, raw[name])
        if problem:
            origin[name], problems[name] = ABSENT, problem
            continue
        frames[name], origin[name], missing[name] = df, mode, lacking

    if "issues" in frames:  # model của annotator lấy từ bảng annotators, pipeline không cần ghi lại
        models = frames["annotators"].set_index("annotator")["model"] if "annotators" in frames else {}
        frames["issues"]["model"] = frames["issues"]["annotator"].map(models)
    return Tables(mode, frames, origin, problems, missing, has_real_files, images)


def _streamlit_demo() -> bool:
    """Công tắc "Xem bằng dữ liệu giả" của bản Streamlit. Bỏ khi bỏ hẳn Streamlit."""
    try:
        import streamlit as st
        return bool(st.session_state.get(DEMO_KEY, False))
    except Exception:
        return False


def load(demo: bool | None = None, folder: Path | None = None) -> Tables:
    """Nạp mọi bảng. `demo=True` bỏ qua file thật; `None` thì đọc công tắc của bản Streamlit.

    `folder`: thư mục bảng thật của bộ dữ liệu đang chọn (data_layer/datasets.py), mặc định REAL_DIR.
    """
    if demo is None:
        demo = _streamlit_demo()
    folder = folder or S.REAL_DIR
    paths = {name: real_path(name, folder) for name in schema.TABLES}
    files = tuple(sorted((name, str(path), path.stat().st_mtime) for name, path in paths.items() if path))
    own_images = folder / "images.zip"
    with _lock:
        if files and not demo:
            return _assemble(REAL, files, _code_version(), True, own_images if own_images.exists() else S.IMAGES_ZIP)
        gt = (("ground_truth", str(S.GT_XML), S.GT_XML.stat().st_mtime),)
        return _assemble(MOCK, gt, _code_version(), bool(files), S.IMAGES_ZIP)


@lru_cache(maxsize=1)
def _sample_zip(version: tuple) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, df in _mock_tables(version).items():
            archive.writestr(f"{name}.csv", df.to_csv(index=False))
    return buffer.getvalue()


def sample_zip() -> bytes:
    """12 bảng giả ở đúng dạng hợp đồng (dùng mã), làm file mẫu cho pipeline."""
    with _lock:
        return _sample_zip(_code_version() + (S.GT_XML.stat().st_mtime,))
