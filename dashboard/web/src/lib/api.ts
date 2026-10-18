// Kiểu dữ liệu khớp với JSON của dashboard/api. Đổi ở backend thì đổi ở đây.
import type { VisualizationSpec } from "vega-embed";

export type FilterName = "run" | "class" | "size" | "annotator";
export type Option = { code: string; label: string };
export type Badge = { kind: "mock" | "partial" | "real"; label: string; hint: string | null };

export type PageInfo = {
  path: string;
  title: string;
  icon: string;
  question: string;
  filters: FilterName[];
  ported: boolean;
  badge: Badge;
};

export type Meta = {
  /** Bộ dữ liệu đang xem; rỗng là bộ mặc định. */
  dataset: string;
  datasets: string[];
  mode: "real" | "mock";
  has_real_files: boolean;
  n_real: number;
  n_tables: number;
  sections: { title: string; pages: PageInfo[] }[];
  options: { scopes: Option[]; classes: string[]; sizes: Option[]; annotators: string[] };
};

export type Cell = string | number | boolean | null;
export type Frame = { columns: string[]; rows: Cell[][] };
export type Kpi = { label: string; value: string | null; hint: string | null; primary: boolean };
export type Tone = "info" | "warning" | "simulated" | "pending" | "empty";
/** Cách hiện một cột bảng (api/blocks.py: col). `percent`: cột 0–100 vẽ thành thanh. */
export type ColumnFormat = { decimals: number | null; suffix: string; percent: boolean };

export type Block =
  | { type: "kpis"; items: Kpi[] }
  | { type: "chart"; title: string; note: string | null; spec: VisualizationSpec; table: Frame | null }
  | { type: "table"; title: string; note: string | null; table: Frame; formats: Record<string, ColumnFormat> }
  | { type: "heading"; title: string; note: string | null }
  | { type: "pending"; title: string; message: string }
  | { type: "notice"; tone: Tone; message: string }
  | { type: "empty"; message: string };

export type Row = { widths: number[]; blocks: Block[] };
export type PageData = { rows: Row[] };

export type IssueItem = { id: string; annotator: string; error_type: string; class_name: string; resolved: boolean };

export type IssueList =
  | { pending: string }
  | { total: number; max_listed: number; reviewers: string[]; items: IssueItem[]; error_types: Option[] };

/** x1, y1, x2, y2 theo điểm ảnh của ảnh cắt. */
export type Box = [number, number, number, number];
export type Layer = "spot" | "submitted" | "truth";

export type IssueDetail = {
  id: string;
  image: string;
  annotator: string;
  reviewer: string;
  created_at: string | null;
  comment: string | null;
  reply: string | null;
  facts: [string, string][];
  has_truth: boolean;
  knows_submitted: boolean;
  crop: { width: number; height: number; boxes: Record<Layer, Box | null> } | null;
  handling: { title: string; detail: string; caption: string | null } | null;
};

export type PatchItem = { id: string; operation: string; decision: string; class_name: string };

/** `hidden`: phần phân tích phía trên đã báo trang chưa có dữ liệu hoặc trống sau khi lọc. */
export type PatchList =
  | { hidden: true }
  | { pending: string }
  | { total: number; max_listed: number; has_truth: boolean; items: PatchItem[] };

/** Ba khung của một bản vá, theo thứ tự trước khi sửa, agent đề xuất, sau khi áp dụng. */
export type PatchLayer = "submitted" | "proposed" | "final";

export type PatchDetail =
  | { id: string; empty: string }
  | {
      id: string;
      issue_id: string;
      image: string;
      operation: string;
      decision: string;
      reviewer: string;
      comment: string | null;
      has_truth: boolean;
      panels: { key: PatchLayer; title: string; has_box: boolean; class_name: string | null }[];
      crop: { width: number; height: number; boxes: Record<PatchLayer | "truth", Box | null> } | null;
    };

export type DataStatus = {
  kpis: { type: "kpis"; items: Kpi[] };
  folder: string;
  notices: { type: "notice"; tone: Tone; message: string }[];
  status: Frame;
  has_sample: boolean;
  vocab: { name: string; codes: [string, string][] }[];
  contract: { name: string; title: string; desc: string; n_required: number; n_optional: number; columns: Frame }[];
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function apiUrl(path: string, params?: URLSearchParams): string {
  const qs = params?.toString();
  return `/api${path}${qs ? `?${qs}` : ""}`;
}

export async function apiGet<T>(path: string, params?: URLSearchParams): Promise<T> {
  const res = await fetch(apiUrl(path, params));
  if (!res.ok) {
    let message = `Máy chủ trả lỗi ${res.status}.`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      // thân lỗi không phải JSON: giữ thông báo mặc định
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}
