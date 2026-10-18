"""Các trang đã chuyển sang API.

`BUILDERS`: trang phân tích dựng bằng khối chung (api/blocks.py), phục vụ ở /api/pages/<path>.
Trang tra cứu có route riêng trong api/main.py vì cần tương tác riêng (chọn issue, tải file).
"""
from api.pages import (
    annotators, classes, cross_annotators, cross_reviewers, fix_agent, fix_annotator, fix_recommendations, overview,
    top_errors,
)

BUILDERS = {
    "tong-quan": overview.build,
    "top-loi": top_errors.build,
    "class-kho": classes.build,
    "annotator": annotators.build,
    "cham-cheo-annotator": cross_annotators.build,
    "cham-cheo-reviewer": cross_reviewers.build,
    "sua-annotator": fix_annotator.build,
    "sua-agent": fix_agent.build,
    "khuyen-nghi-pilot": fix_recommendations.build,
}
CUSTOM = {"chi-tiet-issue", "nguon-du-lieu"}
PORTED = set(BUILDERS) | CUSTOM
