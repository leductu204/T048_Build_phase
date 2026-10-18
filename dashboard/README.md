# Dashboard M22 – khung giao diện

Khung dashboard cho đề M22 (CVAT Issue Analytics). Chưa có file thật nào thì mọi trang chạy trên
**dữ liệu giả** sinh từ bộ đáp án BDD100K trong `sample_data_output1/`. Pipeline xong chặng nào thì
thả bảng của chặng đó vào `dashboard/data_real/`, không phải sửa code giao diện.

## Chạy

Từ thư mục gốc của project:

```
pip install -r requirements.txt
streamlit run dashboard/app.py --server.address localhost
```

Cần `sample_data_output1/annotations.xml` (để sinh số giả) và `images.zip` (để hiện ảnh).
Đã kiểm tra với Python 3.13, Streamlit 1.55, Altair 6.0.

## Giao diện mới: FastAPI + React (đang chuyển)

Streamlit không dùng cho bản deploy chính thức, nên dashboard đang chuyển sang hai phần:

- `api/` (FastAPI) dùng lại nguyên `data_layer/` và `ui/charts.py`. Mỗi trang phân tích trả về một
  danh sách hàng khối (KPI, biểu đồ, bảng, thẻ chờ dữ liệu); biểu đồ là spec Vega-Lite do Altair dựng.
- `web/` (React + Vite + TypeScript, Tailwind, TanStack Query, vega-embed) chỉ vẽ các khối đó.
  Bộ lọc và công tắc dữ liệu giả nằm trên URL, nên chia link là giữ nguyên bộ lọc.

Chạy khi phát triển, hai cửa sổ dòng lệnh:

```
cd dashboard
uvicorn api.main:app --reload --port 8000

cd dashboard/web
npm install
npm run dev          # mở http://localhost:5173
```

Vite chuyển mọi request `/api` sang `http://127.0.0.1:8000`. API chạy cổng khác thì đặt biến môi
trường `M22_API_URL` trước `npm run dev`, ví dụ `M22_API_URL=http://127.0.0.1:8010`.

Đã chuyển: Tổng quan, Chi tiết issue, Nguồn dữ liệu. Các trang khác hiện "sắp có" và vẫn xem được ở
bản Streamlit; hai bản dùng chung `data_layer/` và `catalog.py` nên chạy song song được.

Chuyển thêm một trang phân tích:

1. Tạo `api/pages/<tên>.py` có hàm `build(data, filters) -> list[hàng]`, chép phần tính số từ
   `views/<tên>.py` và đổi `ui.chart(...)`, `ui.kpi_row(...)`, `ui.ready(...)` sang hàm cùng tên trong
   `api/blocks.py`.
2. Thêm vào `BUILDERS` trong `api/pages/__init__.py`. Frontend tự nhận trang; chỉ cần thêm icon của trang
   (tên Material trong `catalog.py`) vào `web/src/lib/icons.tsx` nếu chưa có.
3. Trang cần tương tác riêng (chọn một mục, xem ảnh) thì làm như Chi tiết issue: route riêng trong
   `api/main.py` và một trang trong `web/src/pages/`.

Khi mọi trang đã chuyển thì xoá `app.py`, `views/`, `ui/components.py` và hai đoạn "cầu nối Streamlit"
trong `data_layer/store.py` và `ui/theme.py`.

Giao diện: token màu và chữ ở `web/src/index.css`; màu xám và phông của biểu đồ ở `ui/theme.py` phải khớp
với token đó. Font Be Vietnam Pro (@fontsource) và icon lucide được đóng gói cùng bản build, không tải từ
ngoài, nên VPS không cần ra internet. Dấu bốn góc khung (lớp `.bracketed`) chỉ dành cho thứ đang được chú
ý; dải sọc hổ phách chỉ dành cho số giả.

## Deploy lên Vercel

`vercel.json` ở thư mục gốc khai báo hai service trong cùng một project, chung một domain:

- `api` (gốc `dashboard/`, FastAPI, `api.main:app`) nhận mọi request `/api/*`. Cài gói từ
  `dashboard/requirements.txt` (bản rút gọn, không có torch). Lệnh build chép `sample_data_output1/`
  vào `dashboard/` vì function chỉ đóng gói thư mục gốc của service; `settings.py` tự tìm bản chép đó.
- `web` (gốc `dashboard/web/`, Vite) nhận mọi đường dẫn còn lại; đường dẫn không phải file tĩnh trả
  `index.html` để React Router xử lý.

Frontend gọi `/api/...` cùng domain nên không cần biến môi trường nào. Chạy thử cả hai cùng lúc:
`vercel dev` ở thư mục gốc. Trên Vercel, ổ đĩa chỉ đọc được, nên muốn dùng dữ liệu thật thì commit
bảng vào `dashboard/data_real/`.

## Các trang

| Nhóm | Trang | Trả lời câu hỏi |
|---|---|---|
| Theo đề M22 | Tổng quan | Hai KPI của đề đang là bao nhiêu |
| | Top lỗi | Loại lỗi nào nhiều và lặp lại |
| | Class khó | Class nào khó, dính lỗi gì |
| | Annotator | Ai cần hỗ trợ, về lỗi gì |
| Chấm chéo | Annotator chấm annotator | Không có đáp án thì ai lệch khỏi nhóm |
| | Reviewer chấm annotator | Issue nhiều do annotator yếu hay reviewer khó |
| Đề xuất vs sửa | Reviewer yêu cầu vs annotator sửa | Annotator có sửa đúng điều được yêu cầu |
| | Agent đề xuất vs người áp dụng | Đề xuất của agent có đúng, người duyệt có lọc được cái sai |
| | Khuyến nghị vs kết quả pilot | Khuyến nghị nào được áp dụng, lỗi có giảm |
| Tra cứu | Chi tiết issue | Xem một issue: ảnh, comment, cách xử lý |
| | Nguồn dữ liệu | Chế độ đang chạy, bảng nào còn thiếu, bảng mã, hợp đồng cột |

## Cắm dữ liệu thật

Trang **Nguồn dữ liệu** là nơi tra cứu: trạng thái 12 bảng, bảng mã, cột của từng bảng, và nút
tải **bộ CSV mẫu** (12 bảng giả ở đúng dạng hợp đồng) để làm mẫu khi viết phần xuất của pipeline.

Ba quy tắc:

1. **Cột bắt buộc và cột tuỳ chọn.** Mỗi bảng chỉ cần đủ cột bắt buộc là được nhận. Ví dụ `issues`
   cần 13 cột có ngay sau chặng ingest; các cột của chặng sau (cờ lặp lại, nguồn được quy, kết quả
   sửa) bổ sung dần vào chính file đó. Phần giao diện nào cần cột chưa có thì ghi rõ còn chờ cột
   nào, của chặng nào.
2. **Dữ liệu ghi theo mã, không ghi nhãn tiếng Việt.** Ví dụ loại lỗi ghi `missing_object`, lần
   chạy ghi `batch2_control`. Giá trị ngoài bảng mã làm cả bảng bị từ chối, và trang Nguồn dữ liệu
   nêu đúng giá trị lạ. Cột đúng/sai nhận `true`/`false` hoặc `1`/`0`.
3. **Số thật và số giả không trộn.** Có ít nhất một file thật là dashboard chuyển sang chế độ thật:
   bảng nào chưa có thì để trống chứ không lấy số giả lấp vào. Muốn xem giao diện đầy đủ thì bật
   "Xem bằng dữ liệu giả" ở thanh bên; khi đó mọi bảng đều là số giả.

Đặt file ở `dashboard/data_real/<tên bảng>.csv` (hoặc `.parquet`), rồi tải lại trang. Muốn trỏ sang
thư mục khác, ví dụ thư mục xuất của pipeline, thì đặt biến môi trường `M22_REAL_DIR`.

Thứ tự nên nộp: `issues` cùng `workload` trước (bốn trang theo đề chạy được ngay), rồi các bảng so
khớp của chặng A, rồi `patches`, rồi `recommendations`.

## Sửa bảng mã và hợp đồng

- Đổi chữ hiện trên giao diện: sửa nhãn trong `settings.py`. Mã giữ nguyên.
- Thêm một mã mới (ví dụ một loại lỗi): thêm vào bảng `*_LABELS` tương ứng trong `settings.py`.
- Thêm cột hoặc đổi cột từ tuỳ chọn sang bắt buộc: sửa `data_layer/schema.py`.
- Trang dùng cột tuỳ chọn phải hỏi trước: `ui.ready(data, "Tiêu đề thẻ", issues=["tên_cột"])`
  cho một thẻ, hoặc khai báo `requires` trong `META` cho cả trang.

## Cấu trúc

```
dashboard/
  app.py              điểm vào bản Streamlit: điều hướng, tiêu đề, hàng lọc, công tắc chế độ
  catalog.py          danh mục trang (tiêu đề, câu hỏi, bảng dùng, bộ lọc), dùng chung cho Streamlit và API
  settings.py         đường dẫn, bảng mã và nhãn, ngưỡng
  data_layer/         không phụ thuộc giao diện nào
    schema.py         hợp đồng 12 bảng: cột bắt buộc, cột tuỳ chọn theo chặng, cột dùng mã
    codec.py          đổi mã sang nhãn và kiểm tra giá trị; mọi bảng đều đi qua đây
    mock.py           sinh số giả từ bộ đáp án, xuất ra đúng dạng hợp đồng
    store.py          chọn chế độ thật hoặc giả, nạp bảng, báo phần nào còn thiếu
    filters.py        bộ lọc chung
    contract.py       bảng trạng thái và bảng cột của hợp đồng, cho trang Nguồn dữ liệu
    metrics.py        đếm và chia theo bộ lọc
  api/                FastAPI: main.py (route), params.py (bộ lọc trên URL), blocks.py (khối), pages/
  web/                React: src/components (khối, hàng lọc, khung), src/pages, src/lib (API, URL, theme)
  ui/
    theme.py          màu theo chế độ sáng, tối
    charts.py         các dạng biểu đồ dùng lại
    components.py     tiêu đề trang, hàng lọc, thẻ KPI, thẻ biểu đồ, thẻ "chưa có dữ liệu"
    images.py         cắt ảnh và vẽ box
  views/              mỗi trang một file, có META và render()
  data_real/          thả bảng thật vào đây
```

Thêm trang mới: tạo file trong `views/` có `META` và `render()`, rồi thêm vào `SECTIONS` trong `app.py`.

## Lưu ý về số giả

- Mọi xác suất trong `mock.py` là tham số tự đặt để giao diện có số mà vẽ. Không trích số từ
  chế độ giả vào báo cáo.
- Trang reviewer và trang annotator tự sửa chỉ hiện lại tham số mô phỏng. Trang agent cần
  quyết định duyệt của người thật mới có nghĩa.
- Cột ghi "cần đáp án" trong hợp đồng chỉ tính được vì dữ liệu bán tổng hợp có ground truth.
- Mẫu số của mọi tỷ lệ là "vật đã review": annotation đã review cộng vật bị báo thiếu. Dùng riêng
  số annotation thì class bị bỏ sót gần hết (traffic sign với model COCO) có mẫu số gần 0.
