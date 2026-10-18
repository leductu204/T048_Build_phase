"""Tham số chung trên URL: bộ dữ liệu, công tắc dữ liệu giả và bộ lọc.

Bộ lọc dùng mã (phạm vi `b1_ctrl`, cỡ `small`), không dùng nhãn tiếng Việt, để URL ngắn và
chia sẻ được. Ô lọc nào trang không dùng thì bị bỏ qua, giống hàng lọc bị khoá ở bản Streamlit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Query

import settings as S
from data_layer import datasets, store
from data_layer.filters import Filters


@dataclass(frozen=True)
class Selection:
    scope: str
    classes: tuple
    sizes: tuple  # nhãn, đã đổi từ mã
    annotators: tuple
    hide_sign: bool

    def filters_for(self, meta: dict) -> Filters:
        on = meta["filters"]
        return Filters(
            runs=S.RUN_SCOPE_CODES[self.scope][1] if "run" in on else (),
            classes=self.classes if "class" in on else (),
            sizes=self.sizes if "size" in on else (),
            annotators=self.annotators if "annotator" in on else (),
            hide_sign=self.hide_sign and "class" in on,
        )


def _check(name: str, values: list[str], valid) -> None:
    strange = sorted(set(values) - set(valid))
    if strange:
        raise HTTPException(422, f"Giá trị lạ ở `{name}`: {', '.join(strange)}. Hợp lệ: {', '.join(valid)}")


def selection(
    scope: str = "b1_ctrl",
    classes: Annotated[list[str], Query(alias="class")] = [],
    size: Annotated[list[str], Query()] = [],
    annotator: Annotated[list[str], Query()] = [],
    hide_sign: bool = False,
) -> Selection:
    _check("scope", [scope], S.RUN_SCOPE_CODES)
    _check("class", classes, S.CLASSES)
    _check("size", size, S.SIZE_LABELS)
    return Selection(scope, tuple(classes), tuple(S.SIZE_LABELS[s] for s in size), tuple(annotator), hide_sign)


def source(ds: str = "") -> str:
    """Tên bộ dữ liệu đang chọn; rỗng là bộ mặc định."""
    if ds and ds not in datasets.names():
        raise HTTPException(404, f"Không có bộ dữ liệu `{ds}`.")
    return ds


def dataset(ds: Annotated[str, Depends(source)], demo: bool = False) -> store.Tables:
    return store.load(demo, datasets.folder(ds))
