"""Khối giao diện API gửi cho frontend: hàng KPI, thẻ biểu đồ, thẻ bảng, thẻ chờ dữ liệu, ghi chú.

Một trang phân tích là danh sách hàng; mỗi hàng chia cột theo `widths`, mỗi cột một khối.
Frontend chỉ cần biết vẽ từng loại khối, nên chuyển thêm trang không phải viết thêm React.
Biểu đồ là spec Vega-Lite do ui/charts.py dựng, frontend vẽ bằng vega-embed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

import pandas as pd

from data_layer import store
from data_layer.filters import Filters
from ui import theme

EMPTY = "Không có dữ liệu với bộ lọc hiện tại."


def frame(df: pd.DataFrame) -> dict:
    """Bảng -> {columns, rows}. NaN thành null, thời điểm thành chuỗi ISO."""
    out = json.loads(df.to_json(orient="split", index=False, date_format="iso", force_ascii=False))
    return {"columns": out["columns"], "rows": out["data"]}


def kpis(items: list[tuple[str, str | None, str | None]], primary: tuple[str, ...] = ()) -> dict:
    """Dải KPI. Giá trị None nghĩa là chưa có dữ liệu để tính: frontend hiện gạch ngang, không hiện số 0.

    `primary`: nhãn các KPI chính của đề, được làm nổi trên dải.
    """
    return {"type": "kpis", "items": [{"label": label, "value": value, "hint": hint, "primary": label in primary}
                                      for label, value, hint in items]}


def chart(title: str, figure, note: str | None = None, table: pd.DataFrame | None = None) -> dict:
    """Thẻ biểu đồ. Bảng số đi kèm hiện ra khi người xem bật "Bảng số liệu"."""
    spec = figure.properties(width="container").to_dict()
    spec["config"] = {**spec.get("config", {}), **theme.vega_config()}
    spec["autosize"] = {"type": "fit-x", "contains": "padding"}
    # Số ghi ở đầu thanh dài nhất nằm ngoài vùng vẽ; chừa lề phải để nó không bị cắt.
    spec["padding"] = {"left": 5, "top": 5, "bottom": 5, "right": 40}
    return {"type": "chart", "title": title, "note": note, "spec": spec,
            "table": frame(table) if table is not None else None}


@dataclass(frozen=True)
class Col:
    """Cách hiện một cột của thẻ bảng, thay cho st.column_config của bản Streamlit.

    `decimals`: số chữ số sau dấu phẩy ("%.1f" -> 1). `suffix`: chữ sau số ("%.2f lần" -> " lần").
    `percent`: cột 0–100 hiện thành thanh phần trăm (ui.percent_column).
    """
    label: str
    decimals: int | None = None
    suffix: str = ""
    percent: bool = False


def col(label: str, decimals: int | None = None, suffix: str = "", percent: bool = False) -> Col:
    return Col(label, decimals, suffix, percent)


def table(title: str, df: pd.DataFrame, note: str | None = None, columns: dict[str, str | Col] | None = None) -> dict:
    """Thẻ bảng. `columns`: tên cột -> nhãn hoặc `col(...)`; chỉ hiện các cột này, theo đúng thứ tự."""
    formats = {}
    if columns:
        specs = {name: spec if isinstance(spec, Col) else Col(spec) for name, spec in columns.items()}
        df = df[list(specs)].rename(columns={name: spec.label for name, spec in specs.items()})
        formats = {spec.label: {"decimals": spec.decimals, "suffix": spec.suffix, "percent": spec.percent}
                   for spec in specs.values() if spec.decimals is not None or spec.suffix or spec.percent}
    return {"type": "table", "title": title, "note": note, "table": frame(df), "formats": formats}


def heading(title: str, note: str | None = None) -> dict:
    """Tiêu đề một mục trong trang, cả hàng (st.subheader cùng st.caption của bản Streamlit)."""
    return {"type": "heading", "title": title, "note": note}


def notice(message: str, tone: str = "info") -> dict:
    """Ghi chú cả hàng. `tone`: info, warning, simulated (số phụ thuộc mô phỏng), pending (chờ dữ liệu)."""
    return {"type": "notice", "tone": tone, "message": message}


def empty(message: str = EMPTY) -> dict:
    return {"type": "empty", "message": message}


def ready(data: store.Tables, title: str, **needs: list[str]) -> dict | None:
    """None nếu đủ bảng và cột cho phần này; thiếu thì trả thẻ nói rõ còn chờ gì, giữ nguyên tiêu đề và bố cục."""
    gaps = data.gaps(**needs)
    if not gaps:
        return None
    return {"type": "pending", "title": title, "message": "Chưa có dữ liệu cho phần này. " + " ".join(gaps)}


def row(*blocks: dict, widths: list[float] | None = None) -> dict:
    return {"widths": widths or [1] * len(blocks), "blocks": list(blocks)}


def page(meta: dict, data: store.Tables, build: Callable[[store.Tables, Filters], list[dict]], f: Filters) -> dict:
    """Dựng một trang phân tích, sau khi kiểm tra điều kiện tối thiểu khai báo ở `requires` của trang."""
    gaps = data.gaps(**meta.get("requires", {}))
    if gaps:
        return {"rows": [row(notice("Trang này chưa có dữ liệu. " + " ".join(gaps), tone="pending"))]}
    return {"rows": build(data, f)}
