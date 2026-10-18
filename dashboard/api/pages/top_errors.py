"""Top lỗi: loại lỗi nào nhiều nhất, lặp lại nhiều nhất và xử lý lâu nhất."""
from api import blocks as B
from data_layer import store
from data_layer.filters import Filters
from ui import charts, theme

REPEAT, FIRST = "Lặp lại", "Lần đầu"


def build(data: store.Tables, f: Filters) -> list[dict]:
    issues = f.apply(data["issues"])
    if issues.empty:
        return [B.row(B.empty())]
    recur, timed = data.has("issues", "is_recurrent"), data.has("issues", "resolution_hours")

    by_type = issues.groupby("error_type")
    summary = by_type.size().rename("n").reset_index().sort_values("n", ascending=False)
    summary["open"] = summary["error_type"].map((1 - by_type["resolved"].mean()) * 100)
    order = list(summary["error_type"])

    if recur:
        summary["repeat"] = summary["error_type"].map(by_type["is_recurrent"].mean() * 100)
        t = theme.tokens()
        split = (issues.assign(kind=issues["is_recurrent"].map({True: REPEAT, False: FIRST}))
                 .groupby(["error_type", "kind"]).size().reset_index(name="n"))
        rows = [B.row(B.chart(
            "Số issue theo loại lỗi, tách phần lặp lại",
            charts.hbar_stacked(split, "error_type", "kind", "n", series_order=[REPEAT, FIRST],
                                colors=[t["accent"], t["deemph"]], normalize=False, y_order=order, x_title="Số issue",
                                name="Loại lỗi", series_title="Loại issue", value_title="Số issue"),
            note="Phần màu đậm là issue lặp lại: cùng annotator đã mắc cùng loại lỗi ở một job trước đó. "
                 "Số phần trăm là tỷ trọng trong loại lỗi đó.",
            table=split,
        ))]
    else:
        rows = [B.row(B.chart(
            "Số issue theo loại lỗi",
            charts.hbar(summary, "error_type", "n", x_title="Số issue", order=order, name="Loại lỗi"),
            note="Chưa tách được phần lặp lại vì bảng issues chưa có cột is_recurrent (chặng D · mart).",
            table=summary[["error_type", "n"]],
        ))]

    title = "Trung vị thời gian xử lý theo loại lỗi"
    left = B.ready(data, title, issues=["resolution_hours"])
    if left is None:
        hours = by_type["resolution_hours"].median().rename("hours").reset_index().dropna()
        summary["hours"] = summary["error_type"].map(hours.set_index("error_type")["hours"])
        left = B.chart(title, charts.hbar(hours, "error_type", "hours", x_title="Giờ", fmt=".1f", name="Loại lỗi"),
                       note="Chỉ tính issue đã đóng.")

    columns = {"error_type": "Loại lỗi", "n": "Số issue"}
    if recur:
        columns["repeat"] = B.col("Lặp lại", percent=True)
    if timed and "hours" in summary:
        columns["hours"] = B.col("Trung vị giờ", decimals=1)
    columns["open"] = B.col("Chưa xử lý", percent=True)
    rows.append(B.row(left, B.table("Bảng tổng hợp", summary, columns=columns), widths=[2, 3]))
    return rows
