// Chi tiết issue: danh sách bên trái (đi bằng ↑ ↓), bên phải là ảnh cắt với từng lớp box bật tắt được,
// trao đổi giữa reviewer và annotator, thông tin và cách xử lý.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { CheckCircle2, ImageOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { FilterChip } from "../components/FilterChip";
import { EmptyState, ErrorState, Notice, Panel, Skeleton } from "../components/ui";
import { apiGet, apiUrl, type IssueDetail, type IssueItem, type IssueList, type Layer } from "../lib/api";
import { shortTime } from "../lib/format";
import { apiParams, sourceParams, useView } from "../lib/view";

const ALL = "";
// Cùng màu khung box với dashboard/ui/theme.py: trắng là reviewer, cam là annotator, xanh dương là đáp án.
const LAYERS: { key: Layer; label: string; color: string }[] = [
  { key: "spot", label: "Vùng reviewer đánh dấu", color: "#f0efec" },
  { key: "submitted", label: "Box annotator đã nộp", color: "#eb6834" },
  { key: "truth", label: "Đáp án", color: "#2a78d6" },
];
const ANNOTATOR_COLOR = "#eb6834";

function Kbd({ children }: { children: string }) {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-line-strong bg-surface px-1 font-sans text-[11px] text-ink2">
      {children}
    </kbd>
  );
}

function IssueRows({ items, activeId, onPick }: { items: IssueItem[]; activeId: string; onPick: (id: string) => void }) {
  const active = useRef<HTMLButtonElement>(null);
  // Thân effect để trong ngoặc: scrollIntoView trên Chrome mới trả về Promise, React sẽ tưởng là hàm dọn dẹp.
  useEffect(() => {
    active.current?.scrollIntoView({ block: "nearest" });
  }, [activeId]);
  return (
    <div role="listbox" aria-label="Danh sách issue" className="max-h-72 overflow-y-auto p-1.5 lg:max-h-[calc(100dvh-15rem)]">
      {items.map((item) => {
        const on = item.id === activeId;
        return (
          <button
            key={item.id}
            ref={on ? active : undefined}
            type="button"
            role="option"
            aria-selected={on}
            onClick={() => onPick(item.id)}
            className={`flex w-full flex-col gap-1 rounded-lg px-3 py-2.5 text-left transition-colors ${
              on ? "bracketed bg-soft [--bracket-size:7px]" : "hover:bg-soft/60"
            }`}
          >
            <span className="flex items-center justify-between gap-2">
              <span className="tabular text-[13px] font-semibold text-ink">{item.id}</span>
              {item.resolved ? (
                <span className="inline-flex items-center gap-1 text-[12px] text-muted">
                  <CheckCircle2 aria-hidden className="size-3" /> Đã đóng
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-[12px] text-accent-ink">
                  <span className="size-1.5 rounded-full bg-accent" /> Còn mở
                </span>
              )}
            </span>
            <span className="flex items-center gap-2 text-[13px]">
              <span className="truncate text-ink2">{item.error_type}</span>
              <span className="truncate text-muted">{item.class_name}</span>
              <span
                title={`Annotator ${item.annotator}`}
                className="ml-auto flex size-5 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium text-ink2"
                style={{ borderColor: ANNOTATOR_COLOR }}
              >
                {item.annotator}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function Viewer({
  issue,
  layers,
  toggle,
}: {
  issue: IssueDetail;
  layers: Record<Layer, boolean>;
  toggle: (layer: Layer) => void;
}) {
  const { sp } = useView();
  const src = apiUrl(`/issues/${encodeURIComponent(issue.id)}/crop.jpg`, sourceParams(sp));
  const [state, setState] = useState<{ src: string; ok: boolean } | null>(null);
  const crop = issue.crop;
  const loaded = state?.src === src;
  const broken = loaded && state?.ok === false;

  const why = (layer: Layer) => {
    if (layer === "submitted" && issue.knows_submitted) return "Annotator không vẽ box nào ở đây";
    if (layer === "truth" && !issue.has_truth) return "Bảng issues chưa có box đáp án (cột gx1…)";
    return "Issue không có vùng đánh dấu";
  };

  return (
    <Panel title={issue.id} aside={<span className="truncate pt-0.5 text-[12px] text-muted">{issue.image}</span>}>
      {crop && !broken ? (
        <div
          className="bracketed mx-auto p-2 [--bracket-size:14px]"
          style={{ maxWidth: `calc(68dvh * ${crop.width / crop.height})` }}
        >
          <div className="relative overflow-hidden rounded-md bg-soft" style={{ aspectRatio: `${crop.width} / ${crop.height}` }}>
            {!loaded && <Skeleton className="absolute inset-0 rounded-none" />}
            <img
              key={src}
              src={src}
              alt={`Vùng ảnh quanh issue ${issue.id}`}
              onLoad={() => setState({ src, ok: true })}
              onError={() => setState({ src, ok: false })}
              className={`absolute inset-0 size-full transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
            />
            <svg viewBox={`0 0 ${crop.width} ${crop.height}`} className="absolute inset-0 size-full" aria-hidden>
              {LAYERS.map(({ key, color }) => {
                const box = crop.boxes[key];
                if (!box || !layers[key]) return null;
                const [x1, y1, x2, y2] = box;
                const rect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1, fill: "none", vectorEffect: "non-scaling-stroke" as const };
                return (
                  <g key={key}>
                    <rect {...rect} stroke="rgb(0 0 0 / 0.55)" strokeWidth={4.5} />
                    <rect {...rect} stroke={color} strokeWidth={2} />
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      ) : (
        <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 rounded-md bg-soft text-[13px] text-muted">
          <ImageOff aria-hidden className="size-6" strokeWidth={1.75} />
          Không tìm thấy ảnh này trong file zip.
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2" role="group" aria-label="Lớp box">
        {LAYERS.map(({ key, label, color }) => {
          const present = Boolean(crop?.boxes[key]);
          const on = present && layers[key];
          return (
            <button
              key={key}
              type="button"
              aria-pressed={on}
              disabled={!present}
              title={present ? undefined : why(key)}
              onClick={() => toggle(key)}
              className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-[13px] transition-colors disabled:cursor-not-allowed disabled:border-dashed disabled:opacity-60 ${
                on ? "border-line-strong bg-soft text-ink" : "border-line text-muted enabled:hover:text-ink2"
              }`}
            >
              <span
                className="size-3 rounded-[3px] border-2"
                style={{ borderColor: color, background: on ? color : "transparent", boxShadow: "0 0 0 1px rgb(0 0 0 / 0.25)" }}
              />
              {present ? label : why(key)}
            </button>
          );
        })}
      </div>
    </Panel>
  );
}

function Message({ role, name, time, text }: { role: "reviewer" | "annotator"; name: string; time?: string; text: string | null }) {
  const reviewer = role === "reviewer";
  return (
    <div className="flex gap-3">
      <span
        aria-hidden
        className="flex size-8 shrink-0 items-center justify-center rounded-full border-2 bg-soft text-[12px] font-semibold text-ink2"
        style={{ borderColor: reviewer ? "var(--line-strong)" : ANNOTATOR_COLOR }}
      >
        {name}
      </span>
      <div className="min-w-0 pt-0.5">
        <p className="text-[13px]">
          <span className="font-semibold text-ink">
            {reviewer ? "Reviewer" : "Annotator"} {name}
          </span>
          {time && <span className="ml-2 text-muted">{time}</span>}
        </p>
        <p className="mt-1 text-[14px] leading-relaxed text-ink">
          {text ?? <span className="text-muted">Issue không có nội dung.</span>}
        </p>
      </div>
    </div>
  );
}

function Detail({ id, layers, toggle }: { id: string; layers: Record<Layer, boolean>; toggle: (layer: Layer) => void }) {
  const { sp } = useView();
  const params = sourceParams(sp);
  const query = useQuery({
    queryKey: ["issue", id, params.toString()],
    queryFn: () => apiGet<IssueDetail>(`/issues/${encodeURIComponent(id)}`, params),
    placeholderData: keepPreviousData,
  });
  if (query.isPending) return <Skeleton className="h-[560px]" />;
  if (query.isError) return <ErrorState error={query.error} />;
  const issue = query.data;

  return (
    <div className={`grid gap-4 transition-opacity 2xl:grid-cols-[minmax(0,1fr)_340px] ${query.isPlaceholderData ? "opacity-60" : ""}`}>
      <Viewer issue={issue} layers={layers} toggle={toggle} />
      <div className="grid content-start gap-4 md:grid-cols-2 2xl:grid-cols-1">
        <Panel title="Trao đổi">
          <div className="flex flex-col gap-5">
            <Message role="reviewer" name={issue.reviewer} time={shortTime(issue.created_at)} text={issue.comment} />
            {issue.reply && <Message role="annotator" name={issue.annotator} text={issue.reply} />}
          </div>
        </Panel>
        <Panel title="Thông tin">
          <dl className="text-[13px]">
            {issue.facts.map(([label, value]) => (
              <div key={label} className="grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-3 border-t border-line py-2 first:border-t-0 first:pt-0">
                <dt className="text-muted">{label}</dt>
                <dd className="font-medium break-words text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        {issue.handling && (
          <Panel title="Cách xử lý" className="md:col-span-2 2xl:col-span-1">
            <p className="text-[14px]">
              <span className="font-semibold text-ink">{issue.handling.title}</span>
              <span className="ml-2 text-ink2">{issue.handling.detail}</span>
            </p>
            {issue.handling.caption && <p className="mt-1 text-[13px] text-muted">{issue.handling.caption}</p>}
          </Panel>
        )}
      </div>
    </div>
  );
}

export function IssueDetailPage() {
  const { sp, update } = useView();
  const [layers, setLayers] = useState<Record<Layer, boolean>>({ spot: true, submitted: true, truth: false });
  const type = sp.get("type") ?? ALL;
  const reviewer = sp.get("reviewer") ?? ALL;
  const params = apiParams(sp, { error_type: type, reviewer });
  const query = useQuery({
    queryKey: ["issues", params.toString()],
    queryFn: () => apiGet<IssueList>("/issues", params),
    placeholderData: keepPreviousData,
  });

  const list = query.data && !("pending" in query.data) ? query.data : null;
  const items = list?.items ?? [];
  const index = Math.max(0, items.findIndex((item) => item.id === sp.get("issue")));
  const chosen = items[index];
  const pick = (id: string) => update((next) => next.set("issue", id));
  const choose = (key: string, value: string) =>
    update((next) => {
      if (value) next.set(key, value);
      else next.delete(key);
      next.delete("issue");
    });

  // ↑ ↓ (hoặc j k) chuyển issue ở bất cứ đâu trên trang, trừ khi đang gõ hoặc đang mở danh sách lọc.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
      if (e.target instanceof Element && e.target.closest("input, textarea, select")) return;
      const step = e.key === "ArrowDown" || e.key === "j" ? 1 : e.key === "ArrowUp" || e.key === "k" ? -1 : 0;
      const target = step ? items[index + step] : undefined;
      if (!target) return;
      e.preventDefault();
      update((next) => next.set("issue", target.id));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, index, update]);

  if (query.isPending) return <Skeleton className="h-[600px]" />;
  if (query.isError) return <ErrorState error={query.error} />;
  if (!list) return <Notice tone="pending" message={(query.data as { pending: string }).pending} />;

  const counted =
    `${list.total.toLocaleString("en-US")} issue khớp bộ lọc` +
    (list.total > list.max_listed ? `; danh sách hiện ${list.max_listed} issue đầu` : "");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <FilterChip
          label="Loại lỗi"
          options={[{ code: ALL, label: "Tất cả" }, ...list.error_types]}
          values={[type]}
          active={type !== ALL}
          onChange={([v]) => choose("type", v)}
        />
        <FilterChip
          label="Reviewer"
          options={[{ code: ALL, label: "Tất cả" }, ...list.reviewers.map((r) => ({ code: r, label: r }))]}
          values={[reviewer]}
          active={reviewer !== ALL}
          onChange={([v]) => choose("reviewer", v)}
        />
        <p className="ml-auto text-[13px] text-muted">{counted}</p>
      </div>
      {chosen ? (
        <div className={`grid items-start gap-4 lg:grid-cols-[280px_minmax(0,1fr)] ${query.isPlaceholderData ? "opacity-60" : ""}`}>
          <section className="rounded-xl border border-line bg-surface lg:sticky lg:top-24">
            <header className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
              <h2 className="text-[14px] font-semibold">Issue</h2>
              <span className="flex items-center gap-1 text-[12px] text-muted">
                <Kbd>↑</Kbd>
                <Kbd>↓</Kbd>
                để chuyển
              </span>
            </header>
            <IssueRows items={items} activeId={chosen.id} onPick={pick} />
          </section>
          <Detail
            id={chosen.id}
            layers={layers}
            toggle={(layer) => setLayers((was) => ({ ...was, [layer]: !was[layer] }))}
          />
        </div>
      ) : (
        <EmptyState message="Không có issue nào khớp bộ lọc." />
      )}
    </div>
  );
}
