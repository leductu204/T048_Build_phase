// Trạng thái người xem nằm trên URL: chia link là người nhận thấy đúng bộ lọc đang chọn.
import { useSearchParams } from "react-router";

// Khoá của hàng lọc chung.
const FILTER_KEYS = ["scope", "class", "size", "annotator", "hide_sign"];
// Khoá chọn nguồn số liệu: bộ dữ liệu và công tắc dữ liệu giả.
const SOURCE_KEYS = ["ds", "demo"];
// Khoá gửi lên API. Các khoá khác (tables, type, issue...) chỉ dùng ở frontend.
const API_KEYS = [...FILTER_KEYS, ...SOURCE_KEYS];
// Khoá giữ lại khi chuyển trang.
const SHARED_KEYS = [...API_KEYS, "tables"];

type Extra = Record<string, string | undefined | null>;

export function useView() {
  const [sp, setSp] = useSearchParams();
  const update = (change: (next: URLSearchParams) => void) =>
    setSp(
      (prev) => {
        const next = new URLSearchParams(prev);
        change(next);
        return next;
      },
      { replace: true },
    );
  return {
    sp,
    update,
    demo: sp.get("demo") === "true",
    showTables: sp.get("tables") === "1",
    filtered: FILTER_KEYS.some((key) => sp.has(key)),
    clearFilters: () => update((next) => FILTER_KEYS.forEach((key) => next.delete(key))),
  };
}

function pick(sp: URLSearchParams, keys: string[]): URLSearchParams {
  const out = new URLSearchParams();
  for (const [key, value] of sp) if (keys.includes(key)) out.append(key, value);
  return out;
}

/** Tham số cho một request: bộ lọc và công tắc trên URL, cộng các tham số riêng của request. */
export function apiParams(sp: URLSearchParams, extra: Extra = {}): URLSearchParams {
  const out = pick(sp, API_KEYS);
  for (const [key, value] of Object.entries(extra)) if (value) out.set(key, value);
  return out;
}

/** Chỉ bộ dữ liệu và công tắc dữ liệu giả: cho các request không phụ thuộc bộ lọc. */
export function sourceParams(sp: URLSearchParams): URLSearchParams {
  return pick(sp, SOURCE_KEYS);
}

/** Phần query giữ lại khi bấm sang trang khác. */
export function sharedSearch(sp: URLSearchParams): string {
  const qs = pick(sp, SHARED_KEYS).toString();
  return qs ? `?${qs}` : "";
}
