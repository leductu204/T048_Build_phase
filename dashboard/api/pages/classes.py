"""Class khó: class nào hay bị mở issue, và bị loại lỗi gì."""
import settings as S
from api import blocks as B
from data_layer import metrics, store
from data_layer.filters import Filters
from ui import charts

RATE = "Issue / 100 vật"


def build(data: store.Tables, f: Filters) -> list[dict]:
    issues, work = f.apply(data["issues"]), f.apply(data["workload"])
    if issues.empty or work.empty:
        return [B.row(B.empty())]

    by_class = metrics.rate(issues, work, ["class_name"]).sort_values("n_reviewed", ascending=False)
    grid = metrics.rate_matrix(issues, work, "class_name", "error_group", S.ERROR_GROUPS)
    rows = [B.row(B.chart(
        "Class × nhóm lỗi",
        charts.heatmap(grid, "error_group", "class_name", "rate", low_n="low_n", x_order=S.ERROR_GROUPS,
                       y_order=list(by_class["class_name"]), x_title="Nhóm lỗi", y_title="Class", value_title=RATE),
        note=f"Mỗi ô là số issue trên 100 vật đã review của class đó. Hàng có dưới {S.MIN_REVIEWED} vật "
             "ghi \"ít mẫu\" và không tô màu.",
        table=grid[["class_name", "error_group", "n_issues", "n_reviewed", "rate"]].round(1),
    ))]

    # Class đủ mẫu xếp theo tỷ lệ; class ít mẫu dồn xuống cuối để không dẫn đầu bảng nhờ vài issue.
    ranked = by_class.assign(enough=~by_class["low_n"]).sort_values(["enough", "rate"], ascending=False)
    left = B.chart("Tỷ lệ issue theo class",
                   charts.hbar(ranked, "class_name", "rate", x_title="Issue trên 100 vật đã review", fmt=".1f",
                               order=list(ranked["class_name"]), highlight="enough", name="Class"),
                   note="Thanh xám ở cuối là class ít mẫu, chưa đủ để kết luận.")

    columns = {
        "class_name": "Class",
        "n_reviewed": "Vật đã review",
        "n_issues": "Số issue",
        "rate": B.col(RATE, decimals=1),
    }
    detail = by_class
    if data.has("issues", "is_recurrent"):
        repeat = issues.groupby("class_name")["is_recurrent"].mean().mul(100)
        detail = by_class.assign(repeat=by_class["class_name"].map(repeat))
        columns["repeat"] = B.col("Lặp lại", percent=True)
    rows.append(B.row(left, B.table("Số liệu theo class", detail, columns=columns)))
    return rows
