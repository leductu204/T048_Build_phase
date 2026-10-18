"""Nguồn dữ liệu: chế độ đang chạy, trạng thái từng bảng, bảng mã và hợp đồng cột."""
import settings as S
from api import blocks as B
from data_layer import contract, schema, store


def build(data: store.Tables, folder: str) -> dict:
    """`folder`: nơi chứa bảng thật của bộ dữ liệu đang xem (datasets.where)."""
    n_real = sum(origin == store.REAL for origin in data.origin.values())

    notices = []
    if data.mode == store.MOCK and data.has_real_files:
        notices.append(B.notice("Đang xem bằng dữ liệu giả theo công tắc ở thanh bên. Các file thật đang bị bỏ qua.",
                                tone="simulated"))
    if data.mode == store.REAL:
        notices += [B.notice(f"Bảng `{name}` bị từ chối: {problem}.", tone="warning")
                    for name, problem in data.problems.items() if not problem.startswith("chưa có file")]

    return {
        "kpis": B.kpis([
            ("Chế độ", "Dữ liệu " + data.mode.lower(), "Số thật và số giả không bao giờ trộn trên cùng một màn hình."),
            ("Bảng thật dùng được", f"{n_real}/{len(schema.TABLES)}", None),
            ("Bộ đáp án", "Có" if S.GT_XML.exists() else "Thiếu", "Dùng để sinh số giả và để hiện ảnh."),
        ]),
        "folder": folder,
        "notices": notices,
        "status": B.frame(contract.status(data)),
        "has_sample": S.GT_XML.exists(),
        "vocab": [{"name": name, "codes": [[code, label] for code, label in labels.items()]}
                  for name, labels in S.VOCAB.items()],
        "contract": [
            {"name": name, "title": spec["title"], "desc": spec["desc"],
             "n_required": len(schema.required(name)), "n_optional": len(spec["columns"]) - len(schema.required(name)),
             "columns": B.frame(contract.columns(name))}
            for name, spec in schema.TABLES.items()
        ],
    }
