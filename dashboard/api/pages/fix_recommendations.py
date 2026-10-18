"""Đề xuất vs sửa, phần 3: khuyến nghị ở mức quy trình và kết quả đo lại ở pilot."""
import pandas as pd

import settings as S
from api import blocks as B
from data_layer import store
from data_layer.filters import Filters
from ui import charts

MIN_CLUSTER = 10  # dưới ngần này issue thì thay đổi của cụm chưa đủ tin
DASH = "–"  # ô không đo được ghi gạch ngang thay vì để trống, để không bị đọc nhầm là 0


def _number(fmt: str):
    return lambda v: DASH if pd.isna(v) else format(v, fmt)


def build(data: store.Tables, f: Filters) -> list[dict]:
    recs = f.apply(data["recommendations"])
    if recs.empty:
        return [B.row(B.empty())]
    measured = data.has("recommendations", "rate_control", "rate_pilot")
    with_side = measured and data.has("recommendations", "side_group", "side_rate_control", "side_rate_pilot")

    applied = recs[recs["status"] == S.REC_APPLIED]
    improved = None
    if measured:
        improved = f"{int((applied['rate_pilot'] < applied['rate_control']).sum())}/{len(applied)}"
    rows = [B.row(B.kpis([
        ("Khuyến nghị", f"{len(recs)}", None),
        (S.REC_APPLIED, f"{len(applied)}", None),
        ("Đo được bằng pilot", f"{int(recs['measurable'].sum())}",
         "Khuyến nghị cho model và guideline đo được. Ghi chú coaching và hiệu chỉnh reviewer chỉ sinh tài liệu."),
        ("Cụm giảm lỗi sau pilot", improved, "Trong số khuyến nghị đã áp dụng."),
    ]))]

    title = "Tỷ lệ lỗi của từng cụm: đối chứng so với pilot"
    block = B.ready(data, title, recommendations=["rate_control", "rate_pilot"])
    if block is None:
        moves_rows = []
        for rec in recs[recs["measurable"]].itertuples():
            moves_rows.append((f"{rec.rec_id} · {rec.scope} · {rec.error_group} · {rec.class_name}",
                               rec.rate_control, rec.rate_pilot))
            if with_side and pd.notna(rec.side_rate_control):
                moves_rows.append((f"{rec.rec_id} · lỗi phụ: {rec.side_group}", rec.side_rate_control,
                                   rec.side_rate_pilot))
        moves = pd.DataFrame(moves_rows, columns=["row", "control", "pilot"]).astype({"control": float, "pilot": float})
        if moves.empty:
            block = B.empty("Chưa có khuyến nghị nào đo được bằng pilot.")
        else:
            block = B.chart(
                title,
                charts.dumbbell(moves, "row", "control", "pilot", start_name="Đối chứng", end_name="Pilot",
                                row_order=list(moves["row"]), x_title="Issue trên 100 vật đã review", name="Cụm"),
                note="Cùng ảnh, cùng reviewer, chỉ khác cấu hình. Hàng \"lỗi phụ\" là nhóm lỗi có thể tăng lên "
                     "do chính khuyến nghị đó. Khuyến nghị bị bỏ qua thì hai chấm trùng nhau.",
                table=moves.round(1),
            )
    rows.append(B.row(block))

    view = recs.assign(cluster=recs["scope"] + " · " + recs["error_group"] + " · " + recs["class_name"])
    columns = {"rec_id": "Mã", "cluster": "Cụm lỗi", "status": "Trạng thái"}
    note = "Chưa có số pilot (chặng H), nên bảng mới liệt kê khuyến nghị."
    if measured:
        control, pilot = recs["rate_control"].astype(float), recs["rate_pilot"].astype(float)
        view = view.assign(control=control.map(_number(".1f")), pilot=pilot.map(_number(".1f")),
                           change=(pilot - control).map(_number("+.1f")))
        columns |= {"control": "Đối chứng", "pilot": "Pilot", "change": "Thay đổi"}
        note = f"Tỷ lệ là issue trên 100 vật đã review. Ô ghi \"{DASH}\" là khuyến nghị không đo được."
        if data.has("recommendations", "n_control"):
            view["sample"] = recs["n_control"].map(lambda n: "Ít mẫu" if pd.isna(n) or n < MIN_CLUSTER else "Đủ mẫu")
            columns["sample"] = "Cỡ mẫu"
            note += f" Cụm có dưới {MIN_CLUSTER} issue ở lần đối chứng ghi \"Ít mẫu\"."
        if with_side:
            view["side"] = [f"{g}: {a:.1f} lên {b:.1f}" if pd.notna(a) else "" for g, a, b in
                            zip(recs["side_group"], recs["side_rate_control"], recs["side_rate_pilot"])]
            columns["side"] = "Lỗi phụ"
    columns["attributed_source"] = "Nguồn"
    columns["action"] = "Hành động đề xuất"
    rows.append(B.row(B.table("Danh sách khuyến nghị", view[list(columns)], note=note, columns=columns)))
    return rows
