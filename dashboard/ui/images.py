"""Đọc ảnh thẳng từ file zip, cắt vùng quanh vật và vẽ box.

`view()` tính vùng cắt mà chưa đọc điểm ảnh; `View.place()` đổi toạ độ box sang ảnh cắt.
Frontend dùng hai thứ này để tự vẽ box (bật tắt từng lớp được); bản Streamlit dùng `crop()`,
vẽ sẵn box lên ảnh.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

import settings as S

Box = tuple[float, float, float, float]


@lru_cache(maxsize=64)
def _read(archive: str, mtime: float, name: str) -> bytes | None:
    with zipfile.ZipFile(archive) as zf:
        try:
            return zf.read(name)
        except KeyError:
            return None


def _raw(archive: Path, name: str) -> bytes | None:
    """Ảnh `name` trong file zip; khoá đệm gồm thời điểm sửa file, nên thay zip là đọc lại."""
    if not archive.exists():
        return None
    return _read(str(archive), archive.stat().st_mtime, name)


def box_of(row, prefix: str) -> Box | None:
    """Lấy box từ bốn cột <prefix>x1, y1, x2, y2; None nếu thiếu."""
    values = [row.get(f"{prefix}{k}") for k in ("x1", "y1", "x2", "y2")]
    return None if any(pd.isna(v) for v in values) else tuple(float(v) for v in values)


@dataclass(frozen=True)
class View:
    """Một vùng cắt của ảnh gốc, phóng to `scale` lần."""
    name: str
    left: int
    top: int
    right: int
    bottom: int
    scale: float
    archive: Path = S.IMAGES_ZIP

    @property
    def width(self) -> int:
        return round((self.right - self.left) * self.scale)

    @property
    def height(self) -> int:
        return round((self.bottom - self.top) * self.scale)

    def place(self, box: Box | None) -> Box | None:
        """Toạ độ ảnh gốc -> toạ độ trên ảnh cắt đã phóng to."""
        if box is None:
            return None
        xs = sorted(((box[0] - self.left) * self.scale, (box[2] - self.left) * self.scale))
        ys = sorted(((box[1] - self.top) * self.scale, (box[3] - self.top) * self.scale))
        return xs[0], ys[0], xs[1], ys[1]

    def image(self) -> Image.Image:
        img = Image.open(io.BytesIO(_raw(self.archive, self.name))).convert("RGB")
        out = img.crop((self.left, self.top, self.right, self.bottom))
        if self.scale > 1:
            out = out.resize((self.width, self.height), Image.LANCZOS)
        return out


def view(name: str, frame: list[Box | None], min_width: int = 520, archive: Path = S.IMAGES_ZIP) -> View | None:
    """Vùng cắt quanh các box trong `frame`, chừa lề để thấy bối cảnh. None nếu không có ảnh.

    Truyền cùng một `frame` cho nhiều ảnh để chúng cắt đúng một vùng và so được với nhau.
    `archive`: file zip chứa ảnh của bộ dữ liệu đang xem.
    """
    raw = _raw(archive, name)
    if raw is None:
        return None
    width, height = Image.open(io.BytesIO(raw)).size  # chỉ đọc phần đầu file
    anchors = [b for b in frame if b is not None]
    if anchors:
        x1, y1 = min(b[0] for b in anchors), min(b[1] for b in anchors)
        x2, y2 = max(b[2] for b in anchors), max(b[3] for b in anchors)
        margin = max(70.0, 1.2 * max(x2 - x1, y2 - y1))
        left, top = max(0, int(x1 - margin)), max(0, int(y1 - margin))
        right, bottom = min(width, int(x2 + margin)), min(height, int(y2 + margin))
    else:
        left, top, right, bottom = 0, 0, width, height
    scale = min(6.0, max(1.0, min_width / (right - left)))
    return View(name, left, top, right, bottom, scale, archive)


def crop(name: str, boxes: list[tuple[Box | None, str]], frame: list[Box | None] | None = None,
         min_width: int = 520) -> Image.Image | None:
    """Cắt vùng quanh các box rồi vẽ khung. `frame`: các box quyết định vùng cắt."""
    cut = view(name, frame if frame is not None else [b for b, _ in boxes], min_width)
    if cut is None:
        return None
    out = cut.image()
    draw = ImageDraw.Draw(out)
    for box, color in boxes:
        placed = cut.place(box)
        if placed is not None:
            draw.rectangle(list(placed), outline=color, width=3)
    return out
