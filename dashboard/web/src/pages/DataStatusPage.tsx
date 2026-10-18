// Nguồn dữ liệu: chế độ đang chạy, trạng thái 12 bảng, file mẫu, bảng mã và hợp đồng cột.
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, Download, Search } from "lucide-react";
import { useState, type ReactNode } from "react";
import { KpiStrip } from "../components/Blocks";
import { DataTable } from "../components/DataTable";
import { ErrorState, Notice, PageSkeleton, Panel } from "../components/ui";
import { apiGet, apiUrl, type Cell, type DataStatus, type Frame } from "../lib/api";
import { sourceParams, useView } from "../lib/view";

// Chữ ở cột "Nguồn" do backend ghi (data_layer/store.py: REAL, MOCK, ABSENT).
const ORIGIN_DOT: Record<string, string> = { "Thật": "bg-good", "Giả": "bg-mock", "Chưa có": "border border-muted" };

function Code({ children }: { children: ReactNode }) {
  return <code className="rounded bg-soft px-1 py-px font-mono text-[0.86em] text-ink">{children}</code>;
}

function Section({ title, note, children }: { title: string; note: string; children: ReactNode }) {
  return (
    <section className="mt-12">
      <h2 className="text-[20px] font-semibold tracking-[-0.01em]">{title}</h2>
      <p className="mt-1.5 max-w-[46em] text-[14px] leading-relaxed text-ink2">{note}</p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Expander({ summary, meta, open, children }: { summary: string; meta?: string; open?: boolean; children: ReactNode }) {
  return (
    <details open={open} className="group rounded-xl border border-line bg-surface open:pb-4">
      <summary className="flex cursor-pointer list-none items-center gap-2.5 rounded-xl px-4 py-3 select-none hover:bg-soft/50 [&::-webkit-details-marker]:hidden">
        <ChevronRight aria-hidden className="size-4 shrink-0 text-muted transition-transform group-open:rotate-90" />
        <span className="font-mono text-[13px] font-medium text-ink">{summary}</span>
        {meta && <span className="truncate text-[13px] text-muted">{meta}</span>}
      </summary>
      <div className="px-4 pt-1">{children}</div>
    </details>
  );
}

function statusCell(value: Cell, column: string): ReactNode | undefined {
  if (column === "Nguồn" && typeof value === "string")
    return (
      <span className="inline-flex items-center gap-2 whitespace-nowrap">
        <span className={`size-2 rounded-full ${ORIGIN_DOT[value] ?? "bg-muted"}`} />
        {value}
      </span>
    );
  if (column === "Bảng" && typeof value === "string") return <Code>{value}</Code>;
  if (column === "Ghi chú" && value === "Đủ cột") return <span className="text-good">{value}</span>;
  return undefined;
}

/** Bỏ dấu và viết thường, để gõ "bat buoc" vẫn tìm ra "Bắt buộc". */
const fold = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();

function matchRows(frame: Frame, q: string): Frame {
  return { ...frame, rows: frame.rows.filter((row) => row.some((v) => v !== null && fold(String(v)).includes(q))) };
}

function Contract({ tables }: { tables: DataStatus["contract"] }) {
  const [query, setQuery] = useState("");
  const q = fold(query.trim());
  const shown = tables
    .map((t) => {
      const named = !q || fold(`${t.name} ${t.title} ${t.desc}`).includes(q);
      return { ...t, columns: named ? t.columns : matchRows(t.columns, q), hit: Boolean(q) };
    })
    .filter((t) => t.columns.rows.length > 0);
  return (
    <>
      <label className="relative mb-4 block max-w-md">
        <span className="sr-only">Tìm trong hợp đồng cột</span>
        <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Tìm bảng, cột hoặc ý nghĩa"
          className="h-9 w-full rounded-lg border border-line-strong bg-surface pr-3 pl-9 text-[14px] text-ink placeholder:text-muted focus-visible:border-accent"
        />
      </label>
      <div className="flex flex-col gap-2">
        {shown.map((t) => (
          <Expander
            key={t.name}
            summary={t.name}
            meta={`${t.title}, ${t.n_required} cột bắt buộc, ${t.n_optional} tuỳ chọn`}
            open={t.hit || undefined}
          >
            <p className="mb-3 text-[13px] leading-relaxed text-ink2">{t.desc}</p>
            <DataTable frame={t.columns} maxHeight={520} render={(v, col) => (col === "Cột" && typeof v === "string" ? <Code>{v}</Code> : undefined)} />
          </Expander>
        ))}
        {shown.length === 0 && <p className="text-[14px] text-muted">Không có bảng hay cột nào khớp “{query}”.</p>}
      </div>
    </>
  );
}

export function DataStatusPage() {
  const { sp } = useView();
  const params = sourceParams(sp);
  const query = useQuery({
    queryKey: ["data-status", params.toString()],
    queryFn: () => apiGet<DataStatus>("/data-status", params),
  });
  if (query.isPending) return <PageSkeleton />;
  if (query.isError) return <ErrorState error={query.error} />;
  const d = query.data;
  const classes = d.vocab.find((v) => v.name === "class");

  return (
    <div>
      <KpiStrip items={d.kpis.items} />
      <p className="mt-5 max-w-[52em] text-[14px] leading-relaxed text-ink2">
        Bảng thật của bộ này nằm ở <Code>{d.folder}/</Code>, tên <Code>&lt;tên bảng&gt;.csv</Code> hoặc <Code>.parquet</Code>.
        Chỉ cần một file là dashboard chuyển sang số thật; bảng nào chưa có thì các trang ghi rõ còn chờ gì.
      </p>
      {d.notices.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          {d.notices.map((n, i) => (
            <Notice key={i} tone={n.tone} message={n.message} />
          ))}
        </div>
      )}
      <div className="mt-6">
        <Panel title="Trạng thái từng bảng" note="Bảng chỉ cần đủ cột bắt buộc là được nhận. Cột tuỳ chọn bổ sung dần theo từng chặng.">
          <DataTable frame={d.status} maxHeight={640} render={statusCell} />
        </Panel>
      </div>

      <Section
        title="File mẫu"
        note="12 bảng giả ở đúng dạng hợp đồng: đúng tên cột, ghi theo mã. Dùng làm mẫu khi viết phần xuất của pipeline."
      >
        {d.has_sample ? (
          <a
            href={apiUrl("/sample.zip", params)}
            download
            className="inline-flex h-9 items-center gap-2 rounded-lg bg-accent-strong px-4 text-[14px] font-medium text-white hover:brightness-110"
          >
            <Download aria-hidden className="size-4" />
            Tải bộ CSV mẫu
          </a>
        ) : (
          <p className="text-[14px] text-muted">Cần bộ đáp án trong sample_data_output1/ để sinh file mẫu.</p>
        )}
      </Section>

      <Section
        title="Bảng mã"
        note="Dữ liệu ghi theo mã ở cột trái, giao diện hiện nhãn ở cột phải. Giá trị ngoài bảng mã làm cả bảng bị từ chối, kèm thông báo nêu đúng giá trị lạ. Đổi nhãn thì sửa settings.py; mã giữ nguyên."
      >
        {classes && (
          <div className="mb-4 flex flex-wrap items-center gap-1.5 text-[14px]">
            <span className="mr-1 font-mono text-[13px] font-medium">class</span>
            {classes.codes.map(([code]) => (
              <span key={code} className="rounded-full border border-line px-2.5 py-0.5 text-[13px] text-ink2">
                {code}
              </span>
            ))}
          </div>
        )}
        <div className="grid items-start gap-2 md:grid-cols-2">
          {d.vocab
            .filter((v) => v.name !== "class")
            .map((v) => (
              <Expander key={v.name} summary={v.name} meta={`${v.codes.length} mã`}>
                <DataTable
                  frame={{ columns: ["Mã trong dữ liệu", "Nhãn trên giao diện"], rows: v.codes }}
                  render={(value, col) => (col === "Mã trong dữ liệu" && typeof value === "string" ? <Code>{value}</Code> : undefined)}
                />
              </Expander>
            ))}
        </div>
      </Section>

      <Section title="Hợp đồng cột" note="Cột của từng bảng, khi nào cần và giá trị hợp lệ. Cột ghi “cần đáp án” chỉ tính được khi có ground truth.">
        <Contract tables={d.contract} />
      </Section>
    </div>
  );
}
