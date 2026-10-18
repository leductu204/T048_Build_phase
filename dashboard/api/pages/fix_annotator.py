"""Đề xuất vs sửa, phần 1: reviewer yêu cầu gì và annotator thực sự sửa gì."""
import altair as alt
import pandas as pd

import settings as S
from api import blocks as B
from data_layer import store
from data_layer.filters import Filters
from ui import charts

CHANGES = [*S.ACTIONS, S.NO_CHANGE]


def build(data: store.Tables, f: Filters) -> list[dict]:
    issues = f.apply(data["issues"])
    mine = issues[issues["fix_arm"] == S.ARM_ANNOTATOR]
    done = mine[mine["fix_outcome"] != S.OUTCOME_OPEN]
    if done.empty:
        return [B.row(B.empty())]
    rows = [B.row(B.notice(
        "Khi cách annotator phản hồi issue là mô phỏng, trang này chỉ hiện lại tham số đã đặt. "
        "Với dữ liệu thật, nó cần bản chụp annotation trước và sau khi issue được đóng.", tone="simulated"))]

    # Có đáp án thì loại được issue báo nhầm: đóng mà không sửa một issue báo nhầm là đúng.
    checked = data.has("issues", "is_false_alarm")
    silent = done[done["fix_outcome"] == S.OUTCOME_SILENT]
    if checked:
        silent = silent[~silent["is_false_alarm"].eq(True)]
    still_wrong = f"{done['still_wrong'].mean():.0%}" if data.has("issues", "still_wrong") else None
    rows.append(B.row(B.kpis([
        ("Annotator tự xử lý", f"{len(mine):,}", "Số issue không đi qua luồng agent."),
        (S.OUTCOME_RIGHT, f"{(done['fix_outcome'] == S.OUTCOME_RIGHT).mean():.0%}", "Tính trên issue đã đóng."),
        (S.OUTCOME_SILENT, f"{len(silent) / len(done):.0%}",
         "Issue bị đóng trong khi annotation không đổi. " +
         ("Đã loại issue báo nhầm." if checked else "Chưa loại được issue báo nhầm vì chưa có đáp án.")),
        ("Đóng rồi vẫn sai", still_wrong, "Issue đã đóng mà annotation vẫn sai. Cần đáp án."),
    ])))

    grid = pd.MultiIndex.from_product([S.ACTIONS, CHANGES], names=["requested", "observed"])
    cells = (done.groupby(["requested_action", "observed_change"]).size()
             .reindex(grid, fill_value=0).rename("n").reset_index())
    cells["share"] = cells["n"] / cells.groupby("requested")["n"].transform("sum").replace(0, 1)
    left = B.chart(
        "Thao tác được yêu cầu × thay đổi thực tế",
        charts.heatmap(cells, "observed", "requested", "share", fmt=".0%", x_order=CHANGES, y_order=S.ACTIONS,
                       x_title="Thay đổi thực tế trên annotation", y_title="Reviewer yêu cầu", step=44, vmax=1.0,
                       show_legend=False,
                       tooltip=[alt.Tooltip("requested:N", title="Reviewer yêu cầu"),
                                alt.Tooltip("observed:N", title="Thay đổi thực tế"),
                                alt.Tooltip("n:Q", title="Số issue"),
                                alt.Tooltip("share:Q", title="Phần của hàng", format=".0%")]),
        note=f"Mỗi hàng cộng lại bằng 100%. Đường chéo đậm là sửa đúng yêu cầu; cột \"{S.NO_CHANGE}\" đậm là "
             "đóng issue mà không sửa.",
        table=cells,
    )
    by_person = mine.groupby(["annotator", "fix_outcome"]).size().reset_index(name="n")
    right = B.chart(
        "Kết quả xử lý theo annotator",
        charts.hbar_stacked(by_person, "annotator", "fix_outcome", "n", series_order=S.FIX_OUTCOMES,
                            legend_columns=2, name="Annotator", series_title="Kết quả", value_title="Số issue"),
        note="Tính trên mọi issue annotator tự xử lý, kể cả issue còn mở.",
        table=by_person,
    )
    rows.append(B.row(left, right))

    rows.append(B.row(B.table(
        "Issue bị đóng mà không sửa" + (", trong khi lỗi có thật" if checked else ""),
        silent[["issue_id", "annotator", "reviewer", "class_name", "error_type", "requested_action", "comment"]].head(200),
        note=f"{len(silent):,} issue. Đây là danh sách nên xem lại đầu tiên.",
        columns={"issue_id": "Issue", "annotator": "Annotator", "reviewer": "Reviewer", "class_name": "Class",
                 "error_type": "Loại lỗi", "requested_action": "Yêu cầu", "comment": "Comment"},
    )))
    return rows
