"""Chấm chéo, phần 1: so nhãn của các annotator với nhau, không cần đáp án."""
import altair as alt
import pandas as pd

from api import blocks as B
from data_layer import store
from data_layer.filters import Filters
from ui import charts

COUNTS = ["n_same", "n_class_diff", "n_box_off", "n_only_a", "n_only_b"]
IN_GT, NOT_IN_GT, UNCHECKED = "Có trong đáp án", "Không có trong đáp án", "Chưa đối chiếu đáp án"
GAPS = {"n_class_diff": "Khác class", "n_box_off": "Lệch box", "n_only_a": "Chỉ mình vẽ", "n_only_b": "Chỉ bên kia vẽ"}


def build(data: store.Tables, f: Filters) -> list[dict]:
    pairs = f.apply(data["pair_agreement"]).groupby(["annotator_a", "annotator_b"], as_index=False)[COUNTS].sum()
    pairs["total"] = pairs[COUNTS].sum(axis=1)
    pairs = pairs[pairs["total"] > 0]
    if pairs.empty:
        return [B.row(B.empty("Cần ít nhất hai annotator có dữ liệu trong bộ lọc hiện tại."))]
    pairs["agreement"] = pairs["n_same"] / pairs["total"]
    names = sorted(set(pairs["annotator_a"]))
    votes = f.apply(data["object_votes"]) if data.available("object_votes") else None
    checked = data.has("object_votes", "in_gt")

    unique = pairs[pairs["annotator_a"] < pairs["annotator_b"]]
    best, worst = unique.loc[unique["agreement"].idxmax()], unique.loc[unique["agreement"].idxmin()]
    unseen = f"{int((votes['in_gt'] & (votes['n_votes'] == 0)).sum()):,}" if checked else None
    rows = [B.row(B.kpis([
        ("Đồng thuận trung bình", f"{unique['agreement'].mean():.0%}",
         "Trong số vật ít nhất một bên vẽ, bao nhiêu phần hai bên vẽ trùng nhau và cùng class."),
        ("Cặp giống nhau nhất", f"{best['annotator_a']} và {best['annotator_b']} · {best['agreement']:.0%}", None),
        ("Cặp khác nhau nhất", f"{worst['annotator_a']} và {worst['annotator_b']} · {worst['agreement']:.0%}", None),
        ("Vật không ai vẽ", unseen,
         "Vật có trong đáp án nhưng không annotator nào vẽ. Chấm chéo không thể thấy những vật này; cần đáp án."),
    ]))]

    left = B.chart(
        "Ma trận đồng thuận từng cặp",
        charts.heatmap(pairs, "annotator_b", "annotator_a", "agreement", fmt=".0%", x_order=names, y_order=names,
                       x_title="So với annotator", y_title="Annotator", value_title="Đồng thuận", step=44),
        note="Cặp đồng thuận cao thường dùng chung họ model. Đồng thuận cao không có nghĩa là đúng.",
        table=pairs[["annotator_a", "annotator_b", *COUNTS, "agreement"]].round(3),
    )
    title = "Mỗi vật được mấy annotator vẽ"
    right = B.ready(data, title, object_votes=[])
    if right is None:
        n_people = data["pair_agreement"]["annotator_a"].nunique()
        order = [f"{k} annotator vẽ" for k in range(n_people, -1, -1)]
        kind = votes["in_gt"].map({True: IN_GT, False: NOT_IN_GT}) if checked else UNCHECKED
        tally = (votes.assign(row=votes["n_votes"].astype(str) + " annotator vẽ", kind=kind)
                 .groupby(["row", "kind"]).size().reset_index(name="n"))
        note = "Vật chỉ một người vẽ phần lớn là box thừa. Vật nửa số người vẽ là chỗ guideline chưa rõ."
        right = B.chart(
            title,
            charts.hbar_stacked(tally, "row", "kind", "n", normalize=False, y_order=order, x_title="Số vật",
                                series_order=[IN_GT, NOT_IN_GT] if checked else [UNCHECKED],
                                name="Số phiếu", series_title="Đối chiếu đáp án", value_title="Số vật"),
            note=note + (" Phần màu cần đáp án mới tô được." if checked else
                         " Chưa có cột in_gt nên chưa tách được vật thật với box thừa."),
            table=tally,
        )
    rows.append(B.row(left, right))

    mine = pairs.groupby("annotator_a", as_index=False)[[*COUNTS, "total"]].sum()
    gaps = mine.melt(id_vars=["annotator_a", "total"], value_vars=list(GAPS), var_name="kind", value_name="n")
    gaps["kind"] = gaps["kind"].map(GAPS)
    gaps["share"] = gaps["n"] / gaps["total"]
    rows.append(B.row(B.chart(
        "Mỗi annotator bất đồng với người khác ở đâu",
        charts.hbar_stacked(gaps, "annotator_a", "kind", "share", series_order=list(GAPS.values()), normalize=False,
                            axis_format=".0%", labels=False, y_order=names, name="Annotator",
                            series_title="Kiểu bất đồng", value_title="Phần vật",
                            x_title="Phần vật bất đồng, tính trên mọi cặp có annotator này"),
        note="Thanh càng dài càng lệch khỏi nhóm. \"Chỉ bên kia vẽ\" dài nghĩa là annotator này hay bỏ sót.",
        table=gaps[["annotator_a", "kind", "n", "share"]].round(3),
    )))

    rows.append(B.row(B.heading("Chấm chéo có thay được đáp án không?",
                                "Hai biểu đồ này cần đáp án. Chúng chỉ để kiểm tra xem tín hiệu chấm chéo có đáng tin không.")))
    left = B.ready(data, "Theo annotator", gt_scores=[])
    if left is None:
        gt = f.apply(data["gt_scores"]).groupby("annotator")[["n_objects", "n_drawn", "n_correct"]].sum()
        precision, recall = gt["n_correct"] / gt["n_drawn"], gt["n_correct"] / gt["n_objects"]
        people = pd.DataFrame({"f1": 2 * precision * recall / (precision + recall)})
        people["cross"] = pairs.groupby("annotator_a")["agreement"].mean()
        people = people.dropna().rename_axis("annotator").reset_index()
        left = B.chart(
            "Theo annotator",
            charts.scatter(people, "cross", "f1", label="annotator", x_title="Điểm chấm chéo",
                           y_title="F1 theo đáp án",
                           tooltip=[alt.Tooltip("annotator:N", title="Annotator"),
                                    alt.Tooltip("cross:Q", title="Điểm chấm chéo", format=".0%"),
                                    alt.Tooltip("f1:Q", title="F1 theo đáp án", format=".0%")]),
            note="Điểm chấm chéo là đồng thuận trung bình với các annotator còn lại.",
            table=people.round(3),
        )
    right = B.ready(data, "Theo ảnh", image_scores=["error_rate"])
    if right is None:
        img = data["image_scores"]
        r = img["agreement"].corr(img["error_rate"])
        right = B.chart(
            "Theo ảnh",
            charts.scatter(img, "agreement", "error_rate", x_title="Đồng thuận giữa các annotator trên ảnh",
                           y_title="Tỷ lệ lỗi thật trên ảnh", size=45, opacity=0.6,
                           tooltip=[alt.Tooltip("image:N", title="Ảnh"), alt.Tooltip("n_objects:Q", title="Số vật"),
                                    alt.Tooltip("agreement:Q", title="Đồng thuận", format=".0%"),
                                    alt.Tooltip("error_rate:Q", title="Tỷ lệ lỗi thật", format=".0%")]),
            note=f"Mỗi chấm là một ảnh, không theo bộ lọc. Tương quan r = {r:.2f}; "
                 "r âm nghĩa là ảnh càng bất đồng thì càng nhiều lỗi.",
        )
    rows.append(B.row(left, right))
    return rows
