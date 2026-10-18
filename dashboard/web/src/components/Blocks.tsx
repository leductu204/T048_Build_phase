// Vẽ các khối API gửi về (dashboard/api/blocks.py). Thêm loại khối mới thì thêm một nhánh ở BlockView.
import { Hourglass } from "lucide-react";
import type { CSSProperties } from "react";
import type { Block, Kpi, Row } from "../lib/api";
import { useView } from "../lib/view";
import { DataTable } from "./DataTable";
import { EmptyState, Notice, Panel, RichText, Tip } from "./ui";
import { VegaChart } from "./VegaChart";

/**
 * Dải KPI: một khối liền, chia bằng đường mảnh. KPI chính của đề rộng hơn, có góc khung và chữ số lớn hơn,
 * để đọc dải là thấy ngay hai con số đề M22 hỏi.
 */
export function KpiStrip({ items }: { items: Kpi[] }) {
  const cols = items.map((k) => (k.primary ? "minmax(0,1.35fr)" : "minmax(0,1fr)")).join(" ");
  return (
    <div
      className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-(--cols)"
      style={{ "--cols": cols } as CSSProperties}
    >
      {items.map((k, i) => (
        <div
          key={k.label}
          className={`flex flex-col bg-surface px-5 pt-4 pb-5 ${
            k.primary ? "bracketed [--bracket-inset:8px]" : ""
          } ${i === items.length - 1 && items.length % 2 ? "col-span-2 md:col-span-1" : ""}`}
        >
          <div className="text-[13px] text-ink2">
            {k.hint ? <Tip label={k.label} text={k.hint} align={i > items.length / 2 ? "end" : "start"} /> : k.label}
          </div>
          <div
            className={`tabular mt-3 leading-none font-semibold tracking-[-0.03em] ${
              k.primary ? "text-[38px]" : "text-[28px]"
            } ${k.value === null ? "text-muted" : "text-ink"}`}
          >
            {k.value ?? "–"}
          </div>
          {k.value === null ? (
            <p className="mt-2 text-[12px] text-muted">Chưa có dữ liệu để tính</p>
          ) : (
            k.primary && <p className="mt-2 text-[12px] font-medium text-accent-ink">KPI của đề M22</p>
          )}
        </div>
      ))}
    </div>
  );
}

function BlockView({ block }: { block: Block }) {
  const { showTables } = useView();
  switch (block.type) {
    case "kpis":
      return <KpiStrip items={block.items} />;
    case "chart":
      return (
        <Panel title={block.title} note={block.note}>
          <VegaChart spec={block.spec} />
          {showTables && block.table && (
            <div className="mt-5 border-t border-line pt-4">
              <DataTable frame={block.table} maxHeight={280} />
            </div>
          )}
        </Panel>
      );
    case "table":
      return (
        <Panel title={block.title} note={block.note}>
          <DataTable frame={block.table} formats={block.formats} />
        </Panel>
      );
    case "heading":
      return (
        <header className="mt-6">
          <h2 className="text-[20px] font-semibold tracking-[-0.01em]">{block.title}</h2>
          {block.note && (
            <p className="mt-1.5 max-w-[46em] text-[14px] leading-relaxed text-ink2">
              <RichText text={block.note} />
            </p>
          )}
        </header>
      );
    case "pending":
      return (
        <Panel title={block.title}>
          <div className="flex h-full min-h-40 flex-col justify-center rounded-lg border border-dashed border-line-strong px-5 py-6">
            <Hourglass aria-hidden className="size-5 text-muted" strokeWidth={1.75} />
            <p className="mt-3 text-[13px] leading-relaxed text-ink2">
              <RichText text={block.message} />
            </p>
          </div>
        </Panel>
      );
    case "notice":
      return <Notice tone={block.tone} message={block.message} />;
    case "empty":
      return <EmptyState message={block.message} />;
  }
}

export function Rows({ rows }: { rows: Row[] }) {
  return (
    <div className="flex flex-col gap-4">
      {rows.map((row, i) => (
        <div
          key={i}
          className="grid gap-4 lg:grid-cols-(--cols)"
          style={{ "--cols": row.widths.map((w) => `minmax(0, ${w}fr)`).join(" ") } as CSSProperties}
        >
          {row.blocks.map((block, j) => (
            <BlockView key={j} block={block} />
          ))}
        </div>
      ))}
    </div>
  );
}
