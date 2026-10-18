"""Đề xuất vs sửa, phần 2: bản vá agent đưa ra và quyết định của người duyệt."""
import altair as alt
import pandas as pd

import settings as S
from api import blocks as B
from data_layer import store
from data_layer.filters import Filters
from ui import charts

HUMAN = S.DECISIONS[:3]  # ba quyết định do người đưa ra
ACCEPTED = S.DECISIONS[0]
RIGHT, WRONG = "Agent đề xuất đúng", "Agent đề xuất sai"


def _funnel(patches: pd.DataFrame) -> pd.DataFrame:
    steps = [
        ("Issue vào luồng agent", len(patches)),
        ("Map được vào annotation", int(patches["mapped"].sum())),
        ("Agent đưa ra đề xuất", int(patches["proposed"].sum())),
        ("Người đã quyết định", int(patches["decision"].isin(HUMAN).sum())),
        ("Được chấp nhận", int(patches["decision"].isin(HUMAN[:2]).sum())),
        ("Đã ghi vào CVAT", int(patches["applied"].sum())),
        ("Reviewer đóng issue", int(patches["issue_closed"].sum())),
    ]
    df = pd.DataFrame(steps, columns=["step", "n"])
    kept = (df["n"] / df["n"].shift(1).replace(0, 1)).fillna(1)
    df["label"] = [f"{n:,}" if i == 0 else f"{n:,} · giữ {k:.0%}" for i, (n, k) in enumerate(zip(df["n"], kept))]
    return df


def build(data: store.Tables, f: Filters) -> list[dict]:
    patches = f.apply(data["patches"])
    if patches.empty:
        return [B.row(B.empty())]
    rows = [B.row(B.notice(
        "Phần này chỉ có nghĩa khi quyết định chấp nhận hay từ chối do người trong nhóm bấm thật, "
        "và màn hình duyệt không hiện đáp án. Trong dữ liệu giả, các quyết định này là số tự sinh.",
        tone="simulated"))]

    checked = data.has("patches", "proposal_correct")
    proposed = patches[patches["proposed"]]
    decided = patches[patches["decision"].isin(HUMAN)]
    right_share = slipped = None
    if checked:
        right_share = f"{proposed['proposal_correct'].mean():.0%}" if len(proposed) else "–"
        slipped = f"{int(((decided['decision'] == ACCEPTED) & ~decided['proposal_correct']).sum()):,}"
    rows.append(B.row(B.kpis([
        ("Vào luồng agent", f"{len(patches):,}", "Số issue được giao cho agent đề xuất cách sửa."),
        ("Có đề xuất", f"{len(proposed) / len(patches):.0%}", "Phần issue mà agent đưa ra được bản vá."),
        ("Duyệt nguyên văn", f"{(decided['decision'] == ACCEPTED).mean():.0%}" if len(decided) else "–",
         "Trong số đề xuất đã có quyết định, bao nhiêu phần được chấp nhận mà không sửa."),
        ("Đề xuất đúng", right_share, "So với đáp án."),
        ("Đề xuất sai lọt qua", slipped, "Đề xuất sai nhưng vẫn được chấp nhận nguyên văn. Cần đáp án."),
    ])))

    funnel = _funnel(patches)
    left = B.chart("Từ issue đến bản vá đã ghi",
                   charts.hbar(funnel, "step", "n", order=list(funnel["step"]), label="label", x_title="Số issue",
                               name="Bước"),
                   note="\"Giữ\" là phần còn lại so với bước ngay trước.", table=funnel)
    title = "Đề xuất của agent × quyết định của người"
    right = B.ready(data, title, patches=["proposal_correct"])
    if right is None:
        if decided.empty:
            right = B.empty("Chưa có đề xuất nào được quyết định.")
        else:
            verdict = decided["proposal_correct"].map({True: RIGHT, False: WRONG})
            grid = pd.MultiIndex.from_product([[RIGHT, WRONG], HUMAN], names=["agent", "human"])
            cells = (decided.groupby([verdict, "decision"]).size()
                     .reindex(grid, fill_value=0).rename("n").reset_index())
            cells["share"] = cells["n"] / cells.groupby("agent")["n"].transform("sum").replace(0, 1)
            cells["label"] = [f"{n:,} ({s:.0%})" for n, s in zip(cells["n"], cells["share"])]
            right = B.chart(
                title,
                charts.heatmap(cells, "human", "agent", "share", fmt=".0%", label="label", x_order=HUMAN,
                               y_order=[RIGHT, WRONG], x_title="Quyết định của người duyệt", step=64, vmax=1.0,
                               show_legend=False,
                               tooltip=[alt.Tooltip("agent:N", title="Agent"),
                                        alt.Tooltip("human:N", title="Người duyệt"),
                                        alt.Tooltip("n:Q", title="Số đề xuất"),
                                        alt.Tooltip("share:Q", title="Phần của hàng", format=".0%")]),
                note=f"Mỗi hàng cộng lại bằng 100%. Ô cần để ý: hàng dưới, cột \"{ACCEPTED}\" là đề xuất sai "
                     "lọt qua người duyệt.",
                table=cells[["agent", "human", "n", "share"]].round(3),
            )
    rows.append(B.row(left, right))

    by_op = proposed.groupby(["operation", "decision"]).size().reset_index(name="n")
    rows.append(B.row(B.chart(
        "Quyết định theo loại thao tác",
        charts.hbar_stacked(by_op, "operation", "decision", "n", series_order=S.DECISIONS, y_order=S.ACTIONS,
                            name="Thao tác", series_title="Quyết định", value_title="Số đề xuất"),
        note="Thao tác nào bị từ chối hoặc phải sửa lại nhiều thì agent chưa làm tốt thao tác đó.",
        table=by_op,
    )))
    return rows
