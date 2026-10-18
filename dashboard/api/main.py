"""API cho frontend của dashboard M22.

Chạy từ thư mục dashboard/:
    uvicorn api.main:app --reload --port 8000

Tham số chung: `ds=<tên bộ>` để chọn bộ dữ liệu (data_layer/datasets.py), `demo=true` để xem bằng
dữ liệu giả, `dark=true` để biểu đồ theo chế độ tối, và các bộ lọc ở api/params.py.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response

import catalog
import settings as S
from api import blocks as B
from api.pages import BUILDERS, PORTED, data_status, issue_detail, patch_detail
from api.params import Selection, dataset, selection, source
from data_layer import datasets, store
from ui import theme

app = FastAPI(title="M22 · Issue Analytics API")
Data = Annotated[store.Tables, Depends(dataset)]
Source = Annotated[str, Depends(source)]
Sel = Annotated[Selection, Depends(selection)]
ISSUE_PAGE = catalog.PAGES["chi-tiet-issue"]
AGENT_PAGE = catalog.PAGES["sua-agent"]


@app.exception_handler(FileNotFoundError)
def _no_ground_truth(_, error: FileNotFoundError):
    return JSONResponse(status_code=503,
                        content={"detail": f"Không tìm thấy bộ đáp án để dựng dữ liệu giả: {error.filename}"})


@app.exception_handler(datasets.SourceError)
def _no_blob(_, error: datasets.SourceError):
    return JSONResponse(status_code=503, content={"detail": str(error)})


def _icon(meta: dict) -> str:
    """":material/space_dashboard:" -> "space_dashboard" (tên trong bộ Material Symbols)."""
    return meta["icon"].removeprefix(":material/").removesuffix(":")


@app.get("/api/meta")
def meta(data: Data, ds: Source):
    """Danh mục trang, bộ dữ liệu, chế độ dữ liệu và các lựa chọn của hàng lọc."""
    def page(path: str) -> dict:
        m = catalog.PAGES[path]
        kind, label, hint = data.badge(m["tables"])
        return {"path": path, "title": m["title"], "icon": _icon(m), "question": m["question"],
                "filters": sorted(m["filters"]), "ported": path in PORTED,
                "badge": {"kind": kind, "label": label, "hint": hint}}

    return {
        "dataset": ds,
        "datasets": datasets.names(),
        "mode": "real" if data.mode == store.REAL else "mock",
        "has_real_files": data.has_real_files,
        "n_real": sum(origin == store.REAL for origin in data.origin.values()),
        "n_tables": len(data.origin),
        "sections": [{"title": title, "pages": [page(p) for p in paths]} for title, paths in catalog.SECTIONS.items()],
        "options": {
            "scopes": [{"code": code, "label": label} for code, (label, _) in S.RUN_SCOPE_CODES.items()],
            "classes": S.CLASSES,
            "sizes": [{"code": code, "label": label} for code, label in S.SIZE_LABELS.items()],
            "annotators": [str(name) for name in data.annotator_names()],
        },
    }


@app.get("/api/pages/{path}")
def analytics_page(path: str, data: Data, sel: Sel, dark: bool = False):
    if path not in BUILDERS:
        raise HTTPException(404, f"Trang `{path}` chưa chuyển sang API.")
    page_meta = catalog.PAGES[path]
    with theme.using(dark):
        return B.page(page_meta, data, BUILDERS[path], sel.filters_for(page_meta))


@app.get("/api/issues")
def issue_list(data: Data, sel: Sel, error_type: str | None = None, reviewer: str | None = None):
    gaps = data.gaps(**ISSUE_PAGE["requires"])
    if gaps:
        return {"pending": "Trang này chưa có dữ liệu. " + " ".join(gaps)}
    if error_type and error_type not in S.ERROR_TYPE_LABELS:
        raise HTTPException(422, f"Loại lỗi lạ: {error_type}. Hợp lệ: {', '.join(S.ERROR_TYPE_LABELS)}")
    return issue_detail.listing(data, sel.filters_for(ISSUE_PAGE), S.ERROR_TYPE_LABELS.get(error_type or ""), reviewer)


def _issue(data: store.Tables, issue_id: str):
    issue = issue_detail.find(data, issue_id) if data.available("issues") else None
    if issue is None:
        raise HTTPException(404, f"Không có issue {issue_id}.")
    return issue


@app.get("/api/issues/{issue_id}")
def issue_one(issue_id: str, data: Data):
    return issue_detail.detail(data, _issue(data, issue_id))


@app.get("/api/issues/{issue_id}/crop.jpg")
def issue_image(issue_id: str, data: Data):
    content = issue_detail.picture(data, _issue(data, issue_id))
    if content is None:
        raise HTTPException(404, "Không tìm thấy ảnh trong file zip.")
    return Response(content, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/patches")
def patch_list(data: Data, sel: Sel):
    """Danh sách cho phần "Xem một bản vá" ở cuối trang sua-agent."""
    if data.gaps(**AGENT_PAGE["requires"]):
        return {"hidden": True}  # phần phân tích phía trên đã báo trang chưa có dữ liệu
    listed = patch_detail.listing(data, sel.filters_for(AGENT_PAGE))
    gaps = data.gaps(issues=[])
    if listed.get("items") and gaps:
        return {"pending": "Chưa có dữ liệu cho phần này. " + " ".join(gaps)}
    return listed


def _patch(data: store.Tables, patch_id: str):
    patch = patch_detail.find(data, patch_id) if data.available("patches") else None
    if patch is None:
        raise HTTPException(404, f"Không có bản vá {patch_id}.")
    return patch


@app.get("/api/patches/{patch_id}")
def patch_one(patch_id: str, data: Data):
    patch = _patch(data, patch_id)
    issue = patch_detail.issue_of(data, patch)
    if issue is None:
        return {"id": patch_id, "empty": f"Bảng issues không có issue {patch['issue_id']} của bản vá này."}
    return patch_detail.detail(data, patch, issue)


@app.get("/api/patches/{patch_id}/crop.jpg")
def patch_image(patch_id: str, data: Data):
    patch = _patch(data, patch_id)
    issue = patch_detail.issue_of(data, patch)
    content = None if issue is None else patch_detail.picture(data, patch, issue)
    if content is None:
        raise HTTPException(404, "Không tìm thấy ảnh trong file zip.")
    return Response(content, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@app.get("/api/data-status")
def data_status_page(data: Data, ds: Source):
    return data_status.build(data, datasets.where(ds))


@app.get("/api/sample.zip")
def sample_zip():
    if not S.GT_XML.exists():
        raise HTTPException(404, "Cần bộ đáp án để sinh file mẫu.")
    return Response(store.sample_zip(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="m22_bang_mau.zip"'})
