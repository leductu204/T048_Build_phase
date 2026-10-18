"""Hằng số dùng chung của dashboard M22.

Dữ liệu theo hợp đồng dùng MÃ (khoá của các bảng *_LABELS); giao diện dùng NHÃN (giá trị).
Lớp nạp dữ liệu đổi mã sang nhãn đúng một lần (data_layer/codec.py), nên các trang chỉ
thấy nhãn. Muốn đổi chữ hiện trên giao diện thì sửa nhãn ở đây. Mã thì giữ nguyên, vì
pipeline ghi theo mã.
"""
import os
from pathlib import Path

DASH_DIR = Path(__file__).resolve().parent
PROJECT_DIR = DASH_DIR.parent

# Bộ đáp án BDD100K (200 ảnh) dùng để sinh dữ liệu giả và hiển thị ảnh.
SAMPLE_DIR = PROJECT_DIR / "sample_data_output1"
# Service "api" trên Vercel chỉ đóng gói dashboard/, nên lệnh build (vercel.json) chép bộ này vào đây.
if not SAMPLE_DIR.exists():
    SAMPLE_DIR = DASH_DIR / "sample_data_output1"
GT_XML = SAMPLE_DIR / "annotations.xml"
IMAGES_ZIP = SAMPLE_DIR / "images.zip"

# Thả bảng thật vào đây (<tên bảng>.csv hoặc .parquet).
# Đặt biến môi trường M22_REAL_DIR để trỏ sang thư mục khác, ví dụ thư mục xuất của pipeline.
REAL_DIR = Path(os.environ.get("M22_REAL_DIR") or DASH_DIR / "data_real")

# Các bộ dữ liệu khác để chọn trên giao diện (xem data_layer/datasets.py). Trên máy: mỗi thư mục con
# của DATASETS_DIR là một bộ. Trên Vercel Blob: mỗi thư mục BLOB_PREFIX<tên bộ>/ là một bộ.
DATASETS_DIR = Path(os.environ.get("M22_DATASETS_DIR") or DASH_DIR / "datasets")
BLOB_PREFIX = "datasets/"
# Phải khớp chế độ của store lúc tạo; dữ liệu thật thì dùng store private.
BLOB_ACCESS = os.environ.get("M22_BLOB_ACCESS", "private")

# ---------- Bảng mã: mã trong dữ liệu -> nhãn trên giao diện ----------

CLASSES = ["car", "traffic sign", "traffic light", "person", "truck", "bus", "bike", "rider", "motor", "train"]

ERROR_TYPE_LABELS = {
    "missing_object": "Bỏ sót vật", "box_too_small": "Box quá nhỏ", "box_too_large": "Box quá lớn",
    "box_misaligned": "Box lệch", "box_truncated": "Box bị cắt", "wrong_class": "Sai class",
    "duplicate": "Trùng lặp", "false_positive": "Box thừa", "ambiguous": "Mơ hồ",
}
ERROR_GROUP_LABELS = {
    "missing": "Bỏ sót vật", "box": "Lỗi box", "class": "Sai class",
    "duplicate": "Trùng lặp", "extra": "Box thừa", "ambiguous": "Mơ hồ",
}
# Mã loại lỗi -> mã nhóm lỗi. Dashboard tự suy nhóm từ loại, pipeline không cần ghi nhóm cho issue.
ERROR_TYPE_GROUP = {
    "missing_object": "missing", "box_too_small": "box", "box_too_large": "box", "box_misaligned": "box",
    "box_truncated": "box", "wrong_class": "class", "duplicate": "duplicate", "false_positive": "extra",
    "ambiguous": "ambiguous",
}
RUN_LABELS = {"batch1": "Lô 1", "batch2_control": "Lô 2 · đối chứng", "batch2_pilot": "Lô 2 · pilot"}
SIZE_LABELS = {"small": "Nhỏ", "medium": "Vừa", "large": "Lớn"}
# Bốn giá trị đầu là trường source của CVAT; "none" là issue báo thiếu vật.
BOX_SOURCE_LABELS = {"auto": "auto", "semi-auto": "semi-auto", "manual": "manual", "file": "file",
                     "none": "Không có box"}
ATTRIBUTED_LABELS = {"model": "Model", "annotator": "Annotator", "guideline": "Guideline",
                     "reviewer": "Reviewer", "unknown": "Chưa đủ bằng chứng"}
FIX_ARM_LABELS = {"annotator": "Annotator tự sửa", "agent": "Agent đề xuất"}
ACTION_LABELS = {"add_box": "Thêm box", "delete_box": "Xoá box", "change_class": "Đổi class",
                 "adjust_box": "Chỉnh box"}
CHANGE_LABELS = {**ACTION_LABELS, "none": "Không đổi", "pending": "Chưa xử lý"}
FIX_OUTCOME_LABELS = {"as_requested": "Sửa đúng yêu cầu", "different": "Sửa khác yêu cầu",
                      "closed_unchanged": "Đóng mà không sửa", "open": "Chưa xử lý"}
DECISION_LABELS = {"accepted": "Chấp nhận", "edited": "Sửa rồi chấp nhận", "rejected": "Từ chối",
                   "pending": "Chờ duyệt", "unmapped": "Không map được", "no_proposal": "Không đề xuất được"}
REC_STATUS_LABELS = {"proposed": "Đề xuất", "approved": "Đã duyệt", "applied": "Đã áp dụng",
                     "dismissed": "Bỏ qua"}

# Tên bộ mã -> bảng mã. schema.py gắn mỗi cột có giá trị cố định với một bộ mã ở đây.
VOCAB = {
    "class": {c: c for c in CLASSES}, "error_type": ERROR_TYPE_LABELS, "error_group": ERROR_GROUP_LABELS,
    "run": RUN_LABELS, "size": SIZE_LABELS, "box_source": BOX_SOURCE_LABELS, "attributed": ATTRIBUTED_LABELS,
    "fix_arm": FIX_ARM_LABELS, "action": ACTION_LABELS, "change": CHANGE_LABELS,
    "fix_outcome": FIX_OUTCOME_LABELS, "decision": DECISION_LABELS, "rec_status": REC_STATUS_LABELS,
}

# ---------- Nhãn cho các trang: suy ra từ bảng mã, không gõ tay lần hai ----------

SIZES = list(SIZE_LABELS.values())
ERROR_TYPES = list(ERROR_TYPE_LABELS.values())
ERROR_GROUPS = list(ERROR_GROUP_LABELS.values())
TYPE_TO_GROUP = {ERROR_TYPE_LABELS[t]: ERROR_GROUP_LABELS[g] for t, g in ERROR_TYPE_GROUP.items()}

RUN_B1, RUN_CTRL, RUN_PILOT = (RUN_LABELS[k] for k in ("batch1", "batch2_control", "batch2_pilot"))
# Lô 2 chạy hai lần trên cùng ảnh, nên không bao giờ gộp đối chứng với pilot.
# Mã phạm vi -> (nhãn, các lần chạy). Mã dùng trên URL của frontend, nhãn hiện trên giao diện.
RUN_SCOPE_CODES = {
    "b1_ctrl": ("Lô 1 + lô 2 đối chứng", (RUN_B1, RUN_CTRL)),
    "b1": ("Chỉ lô 1", (RUN_B1,)),
    "ctrl": ("Chỉ lô 2 đối chứng", (RUN_CTRL,)),
    "pilot": ("Chỉ lô 2 pilot", (RUN_PILOT,)),
}
RUN_SCOPES = dict(RUN_SCOPE_CODES.values())

ARM_ANNOTATOR, ARM_AGENT = FIX_ARM_LABELS["annotator"], FIX_ARM_LABELS["agent"]
ACTIONS = list(ACTION_LABELS.values())
NO_CHANGE = CHANGE_LABELS["none"]
FIX_OUTCOMES = list(FIX_OUTCOME_LABELS.values())
OUTCOME_RIGHT = FIX_OUTCOME_LABELS["as_requested"]
OUTCOME_SILENT = FIX_OUTCOME_LABELS["closed_unchanged"]
OUTCOME_OPEN = FIX_OUTCOME_LABELS["open"]
# Bốn trạng thái của một đề xuất; ba cái đầu là quyết định của người duyệt.
DECISIONS = [DECISION_LABELS[k] for k in ("accepted", "edited", "rejected", "pending")]
SOURCES = list(ATTRIBUTED_LABELS.values())
BOX_SOURCES = list(BOX_SOURCE_LABELS.values())
NO_BOX = BOX_SOURCE_LABELS["none"]
REC_STATUS = list(REC_STATUS_LABELS.values())
REC_APPLIED = REC_STATUS_LABELS["applied"]

# Dưới ngưỡng này thì ô chỉ hiện "ít mẫu", không tô màu và không kết luận.
MIN_REVIEWED = 30
# Annotator được gắn cờ "cần hỗ trợ" khi tỷ lệ issue vượt trung vị nhóm bấy nhiêu lần.
SUPPORT_RATIO = 1.5
