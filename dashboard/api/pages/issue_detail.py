"""Chi tiết issue: danh sách để chọn, thông tin của một issue, ảnh cắt và toạ độ box trên ảnh đó."""
from __future__ import annotations

import io

import pandas as pd

import settings as S
from data_layer import store
from data_layer.filters import Filters
from ui import images

MAX_LISTED = 500
CROP_WIDTH = 720  # ảnh cắt rộng ít nhất bấy nhiêu điểm ảnh, đủ nét cho khung xem chi tiết
# Các dòng chỉ hiện khi bảng issues đã có cột tương ứng.
LATER_FACTS = [("source", "Nguồn gốc box"), ("attributed_source", "Nguồn lỗi được quy"),
               ("requested_action", "Reviewer yêu cầu"), ("fix_arm", "Luồng xử lý")]


def listing(data: store.Tables, f: Filters, error_type: str | None, reviewer: str | None) -> dict:
    """Các issue khớp bộ lọc, tối đa MAX_LISTED dòng. Danh sách reviewer lấy trước khi lọc theo loại lỗi."""
    issues = f.apply(data["issues"])
    reviewers = sorted(str(r) for r in issues["reviewer"].unique())
    if error_type:
        issues = issues[issues["error_type"] == error_type]
    if reviewer:
        issues = issues[issues["reviewer"] == reviewer]
    shown = issues.head(MAX_LISTED)
    items = [{"id": str(i), "annotator": str(who), "error_type": str(kind), "class_name": str(cls), "resolved": bool(done)}
             for i, who, kind, cls, done in zip(shown["issue_id"], shown["annotator"], shown["error_type"],
                                                shown["class_name"], shown["resolved"])]
    return {"total": len(issues), "max_listed": MAX_LISTED, "reviewers": reviewers, "items": items,
            "error_types": [{"code": code, "label": label} for code, label in S.ERROR_TYPE_LABELS.items()]}


def find(data: store.Tables, issue_id: str) -> pd.Series | None:
    issues = data["issues"]
    match = issues[issues["issue_id"].astype(str) == issue_id]
    return None if match.empty else match.iloc[0]


def _facts(issue: pd.Series, data: store.Tables) -> list[list[str]]:
    annotator = issue["annotator"] + (f" ({issue['model']})" if pd.notna(issue["model"]) else "")
    rows = [("Annotator", annotator), ("Reviewer", issue["reviewer"]),
            ("Job", f"{issue['job_id']} · {issue['run']}"), ("Class", issue["class_name"]),
            ("Loại lỗi", issue["error_type"])]
    if data.has("issues", "is_recurrent"):
        rows.append(("Lặp lại", "Có" if issue["is_recurrent"] else "Không"))
    rows += [(label, issue[col]) for col, label in LATER_FACTS if data.has("issues", col) and pd.notna(issue[col])]
    status = "Đã đóng" if issue["resolved"] else "Còn mở"
    if issue["resolved"] and data.has("issues", "resolution_hours") and pd.notna(issue["resolution_hours"]):
        status += f" sau {issue['resolution_hours']:.1f} giờ"
    rows.append(("Trạng thái", status))
    return [[label, str(value)] for label, value in rows]


def _handling(issue: pd.Series, data: store.Tables) -> dict | None:
    """Issue này đã được xử lý thế nào: bản vá của agent, hoặc kết quả annotator tự sửa."""
    if data.available("patches"):
        patch = data["patches"][data["patches"]["issue_id"] == issue["issue_id"]]
        if not patch.empty:
            p = patch.iloc[0]
            return {"title": f"Bản vá {p['patch_id']}", "detail": f"{p['operation']} · {p['decision']}",
                    "caption": "Đã ghi vào CVAT." if p["applied"] else "Chưa ghi vào CVAT."}
    if data.has("issues", "fix_arm", "fix_outcome") and issue["fix_arm"] == S.ARM_ANNOTATOR \
            and pd.notna(issue["fix_outcome"]):
        caption = None
        if data.has("issues", "observed_change") and pd.notna(issue["observed_change"]):
            caption = f"Thay đổi thực tế trên annotation: {issue['observed_change']}"
        return {"title": S.ARM_ANNOTATOR, "detail": str(issue["fix_outcome"]), "caption": caption}
    return None


def _text(value) -> str | None:
    return None if pd.isna(value) else str(value)


def _boxes(issue: pd.Series, data: store.Tables) -> dict[str, images.Box | None]:
    """Ba lớp box của issue: vùng reviewer đánh dấu, box annotator đã nộp, đáp án (nếu bảng có)."""
    truth = images.box_of(issue, "g") if data.has("issues", "gx1") else None
    return {"spot": images.box_of(issue, "i"), "submitted": images.box_of(issue, "s"), "truth": truth}


def _view(issue: pd.Series, data: store.Tables) -> images.View | None:
    # Vùng cắt luôn gồm cả đáp án, để bật tắt lớp đáp án không làm ảnh nhảy.
    return images.view(issue["image"], list(_boxes(issue, data).values()), min_width=CROP_WIDTH, archive=data.images)


def detail(data: store.Tables, issue: pd.Series) -> dict:
    created = issue["created_at"]
    boxes, cut = _boxes(issue, data), _view(issue, data)
    crop = None
    if cut is not None:
        placed = {name: cut.place(box) for name, box in boxes.items()}
        crop = {"width": cut.width, "height": cut.height,
                "boxes": {name: None if b is None else [round(v, 1) for v in b] for name, b in placed.items()}}
    return {
        "id": str(issue["issue_id"]),
        "image": str(issue["image"]),
        "annotator": str(issue["annotator"]),
        "reviewer": str(issue["reviewer"]),
        "created_at": None if pd.isna(created) else created.isoformat(),
        "comment": _text(issue["comment"]),
        "reply": _text(issue["reply"]) if data.has("issues", "reply") else None,
        "facts": _facts(issue, data),
        "has_truth": data.has("issues", "gx1"),
        "knows_submitted": data.has("issues", "sx1"),
        "crop": crop,
        "handling": _handling(issue, data),
    }


def picture(data: store.Tables, issue: pd.Series) -> bytes | None:
    """Ảnh cắt quanh issue, chưa vẽ box; frontend phủ box lên theo toạ độ trong `detail()`."""
    cut = _view(issue, data)
    if cut is None:
        return None
    buffer = io.BytesIO()
    cut.image().save(buffer, "JPEG", quality=88)
    return buffer.getvalue()
