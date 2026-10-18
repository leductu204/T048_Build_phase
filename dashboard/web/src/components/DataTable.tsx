import type { ReactNode } from "react";
import type { Cell, ColumnFormat, Frame } from "../lib/api";
import { cell } from "../lib/format";

/** Thanh phần trăm cho cột 0–100, như ProgressColumn của bản Streamlit. */
function PercentBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <span className="inline-flex items-center justify-end gap-2">
      <span aria-hidden className="h-1.5 w-16 overflow-hidden rounded-full bg-soft">
        <span className="block h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </span>
      <span className="w-9">{Math.round(value)}%</span>
    </span>
  );
}

function formatted(value: Cell, format: ColumnFormat | undefined): ReactNode {
  if (!format || typeof value !== "number") return cell(value);
  if (format.percent) return <PercentBar value={value} />;
  const text =
    format.decimals === null
      ? cell(value)
      : new Intl.NumberFormat("en-US", { minimumFractionDigits: format.decimals, maximumFractionDigits: format.decimals }).format(value);
  return text + format.suffix;
}

/**
 * Bảng số liệu. Cột toàn số thì căn phải, chữ số đều cột để dễ so; tiêu đề dính trên cùng khi cuộn.
 * `render` vẽ riêng một ô (ví dụ chấm màu trạng thái); trả undefined thì dùng cách hiện mặc định.
 * `formats`: cách hiện từng cột theo nhãn cột (số chữ số, hậu tố, thanh phần trăm).
 */
export function DataTable({
  frame,
  maxHeight = 420,
  render,
  formats = {},
}: {
  frame: Frame;
  maxHeight?: number;
  render?: (value: Cell, column: string) => ReactNode | undefined;
  formats?: Record<string, ColumnFormat>;
}) {
  const numeric = frame.columns.map((_, j) =>
    frame.rows.length > 0 && frame.rows.every((row) => row[j] === null || typeof row[j] === "number"),
  );
  return (
    <div className="overflow-auto rounded-lg border border-line" style={{ maxHeight }}>
      <table className="w-full border-collapse text-[13px]">
        <thead className="sticky top-0 z-10 bg-soft">
          <tr>
            {frame.columns.map((col, j) => (
              <th
                key={col}
                scope="col"
                className={`px-3 py-2 text-[12px] font-medium whitespace-nowrap text-ink2 ${numeric[j] ? "text-right" : "text-left"}`}
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {frame.rows.map((row, i) => (
            <tr key={i} className="border-t border-line hover:bg-soft/50">
              {row.map((value, j) => (
                <td
                  key={j}
                  className={`px-3 py-2 align-top ${numeric[j] ? "tabular text-right whitespace-nowrap" : "text-ink"}`}
                >
                  {render?.(value, frame.columns[j]) ?? formatted(value, formats[frame.columns[j]])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {frame.rows.length === 0 && <p className="px-3 py-4 text-[13px] text-muted">Bảng trống.</p>}
    </div>
  );
}
