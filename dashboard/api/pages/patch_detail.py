"""Xem một bản vá (trang "sua-agent"): danh sách bản vá đã có quyết định, ba khung trước, đề xuất, sau.

Ba khung dùng chung một ảnh cắt; frontend phủ box riêng của từng khung lên theo toạ độ trong `detail()`.
"""
from __future__ import annotations

import io

import pandas as pd

import settings as S
from data_layer import store
from data_layer.filters import Filters
from ui import images

MAX_LISTED = 300
CROP_WIDTH = 600  # mỗi khung chiếm một phần ba hàng, nên ảnh cắt nhỏ hơn ở chi tiết issue
HUMAN = S.DECISIONS[:3]  # ba quyết định do người đưa ra
# Ba khung: (khoá, tiêu đề, bảng lấy box, tiền tố cột box, cột class).
PANELS = [("submitted", "Trước khi sửa", "issue", "s", "class_pred"),
          ("proposed", "Agent đề xuất", "patch", "p", "proposed_class"),
          ("final", "Sau khi áp dụng", "patch", "f", "final_class")]


def listing(data: store.Tables, f: Filters) -> dict:
    """Các bản vá đã có quyết định của người, tối đa MAX_LISTED dòng. `hidden`: phần trên trang đã báo trống."""
    patches = f.apply(data["patches"])
    if patches.empty:
        return {"hidden": True}
    decided = patches[patches["decision"].isin(HUMAN)]
    shown = decided.head(MAX_LISTED)
    items = [{"id": str(p), "operation": str(op), "decision": str(dec), "class_name": str(cls)}
             for p, op, dec, cls in zip(shown["patch_id"], shown["operation"], shown["decision"], shown["class_name"])]
    return {"total": len(decided), "max_listed": MAX_LISTED, "has_truth": data.has("issues", "gx1"), "items": items}


def find(data: store.Tables, patch_id: str) -> pd.Series | None:
    patches = data["patches"]
    match = patches[patches["patch_id"].astype(str) == patch_id]
    return None if match.empty else match.iloc[0]


def issue_of(data: store.Tables, patch: pd.Series) -> pd.Series | None:
    if not data.available("issues"):
        return None
    issues = data["issues"]
    match = issues[issues["issue_id"] == patch["issue_id"]]
    return None if match.empty else match.iloc[0]


def _text(value) -> str | None:
    return None if value is None or pd.isna(value) else str(value)


def _boxes(patch: pd.Series, issue: pd.Series, data: store.Tables) -> dict[str, images.Box | None]:
    """Box của ba khung, cộng đáp án (nếu bảng có) và vùng reviewer đánh dấu (chỉ để định vùng cắt)."""
    rows = {"issue": issue, "patch": patch}
    boxes = {key: images.box_of(rows[table], prefix) for key, _, table, prefix, _ in PANELS}
    boxes["truth"] = images.box_of(issue, "g") if data.has("issues", "gx1") else None
    boxes["spot"] = images.box_of(issue, "i")
    return boxes


def _view(patch: pd.Series, issue: pd.Series, data: store.Tables) -> images.View | None:
    # Vùng cắt luôn gồm cả đáp án, để bật tắt lớp đáp án không làm ảnh nhảy.
    return images.view(issue["image"], list(_boxes(patch, issue, data).values()), min_width=CROP_WIDTH,
                       archive=data.images)


def detail(data: store.Tables, patch: pd.Series, issue: pd.Series) -> dict:
    boxes, cut = _boxes(patch, issue, data), _view(patch, issue, data)
    rows = {"issue": issue, "patch": patch}
    crop = None
    if cut is not None:
        shown = {name: cut.place(box) for name, box in boxes.items() if name != "spot"}
        crop = {"width": cut.width, "height": cut.height,
                "boxes": {name: None if b is None else [round(v, 1) for v in b] for name, b in shown.items()}}
    panels = [{"key": key, "title": title, "has_box": boxes[key] is not None,
               "class_name": _text(rows[table].get(col))}
              for key, title, table, _, col in PANELS]
    return {
        "id": str(patch["patch_id"]),
        "issue_id": str(patch["issue_id"]),
        "image": str(issue["image"]),
        "operation": str(patch["operation"]),
        "decision": str(patch["decision"]),
        "reviewer": str(issue["reviewer"]),
        "comment": _text(issue["comment"]),
        "has_truth": data.has("issues", "gx1"),
        "panels": panels,
        "crop": crop,
    }


def picture(data: store.Tables, patch: pd.Series, issue: pd.Series) -> bytes | None:
    """Ảnh cắt chung của ba khung, chưa vẽ box."""
    cut = _view(patch, issue, data)
    if cut is None:
        return None
    buffer = io.BytesIO()
    cut.image().save(buffer, "JPEG", quality=88)
    return buffer.getvalue()
