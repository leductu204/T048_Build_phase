// Xem một bản vá, ở cuối trang "Agent đề xuất vs người áp dụng": ba ảnh cắt cùng một vùng (trước khi sửa,
// agent đề xuất, sau khi áp dụng), mỗi ảnh phủ box của riêng nó, cộng đáp án khi bật.
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ImageOff } from "lucide-react";
import { useState } from "react";
import { Rows } from "../components/Blocks";
import { EmptyState, ErrorState, Panel, Skeleton, Switch } from "../components/ui";
import { apiGet, apiUrl, type Box, type PatchDetail, type PatchLayer, type PatchList } from "../lib/api";
import { apiParams, sourceParams, useView } from "../lib/view";

type Shown = Exclude<PatchDetail, { empty: string }>;

// Cùng màu khung box với dashboard/ui/theme.py: cam là box đã nộp, xanh lá là agent đề xuất,
// vàng là sau khi áp dụng, xanh dương là đáp án.
const COLORS: Record<PatchLayer | "truth", string> = {
  submitted: "#eb6834",
  proposed: "#1baf7a",
  final: "#eda100",
  truth: "#2a78d6",
};
const LEGEND: { key: PatchLayer | "truth"; label: string }[] = [
  { key: "submitted", label: "Box đã nộp" },
  { key: "proposed", label: "Box agent đề xuất" },
  { key: "final", label: "Box sau khi áp dụng" },
  { key: "truth", label: "Đáp án" },
];

function Frame({ box, color }: { box: Box; color: string }) {
  const [x1, y1, x2, y2] = box;
  const rect = { x: x1, y: y1, width: x2 - x1, height: y2 - y1, fill: "none", vectorEffect: "non-scaling-stroke" as const };
  return (
    <g>
      <rect {...rect} stroke="rgb(0 0 0 / 0.55)" strokeWidth={4.5} />
      <rect {...rect} stroke={color} strokeWidth={2} />
    </g>
  );
}

function Strip({ patch, truth }: { patch: Shown; truth: boolean }) {
  const { sp } = useView();
  // Ba khung dùng chung một ảnh: trình duyệt chỉ tải một lần.
  const src = apiUrl(`/patches/${encodeURIComponent(patch.id)}/crop.jpg`, sourceParams(sp));
  const [state, setState] = useState<{ src: string; ok: boolean } | null>(null);
  const crop = patch.crop;
  const loaded = state?.src === src;
  const broken = loaded && state?.ok === false;

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {patch.panels.map((panel) => {
        const box = crop?.boxes[panel.key];
        const truthBox = truth ? crop?.boxes.truth : null;
        return (
          <figure key={panel.key} className="flex min-w-0 flex-col gap-2">
            <figcaption className="flex items-center gap-2 text-[14px] font-semibold text-ink">
              <span
                aria-hidden
                className="size-3 rounded-[3px] border-2"
                style={{ borderColor: COLORS[panel.key], boxShadow: "0 0 0 1px rgb(0 0 0 / 0.25)" }}
              />
              {panel.title}
            </figcaption>
            {crop && !broken ? (
              <div className="relative overflow-hidden rounded-md bg-soft" style={{ aspectRatio: `${crop.width} / ${crop.height}` }}>
                {!loaded && <Skeleton className="absolute inset-0 rounded-none" />}
                <img
                  key={src}
                  src={src}
                  alt={`${panel.title}, bản vá ${patch.id}`}
                  onLoad={() => setState({ src, ok: true })}
                  onError={() => setState({ src, ok: false })}
                  className={`absolute inset-0 size-full transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
                />
                <svg viewBox={`0 0 ${crop.width} ${crop.height}`} className="absolute inset-0 size-full" aria-hidden>
                  {truthBox && <Frame box={truthBox} color={COLORS.truth} />}
                  {box && <Frame box={box} color={COLORS[panel.key]} />}
                </svg>
              </div>
            ) : (
              <div className="flex aspect-[4/3] flex-col items-center justify-center gap-2 rounded-md bg-soft text-[13px] text-muted">
                <ImageOff aria-hidden className="size-6" strokeWidth={1.75} />
                Không tìm thấy ảnh.
              </div>
            )}
            <p className="text-[13px] text-muted">
              {!panel.has_box ? "Không có box" : panel.class_name ? `Class: ${panel.class_name}` : null}
            </p>
          </figure>
        );
      })}
    </div>
  );
}

function Detail({ id, truth }: { id: string; truth: boolean }) {
  const { sp } = useView();
  const params = sourceParams(sp);
  const query = useQuery({
    queryKey: ["patch", id, params.toString()],
    queryFn: () => apiGet<PatchDetail>(`/patches/${encodeURIComponent(id)}`, params),
    placeholderData: keepPreviousData,
  });
  if (query.isPending) return <Skeleton className="h-[420px]" />;
  if (query.isError) return <ErrorState error={query.error} />;
  if ("empty" in query.data) return <EmptyState message={query.data.empty} />;
  const patch = query.data;
  const legend = LEGEND.filter(({ key }) => key !== "truth" || truth);

  return (
    <Panel
      title={patch.id}
      note={`Issue ${patch.issue_id} · ${patch.operation} · ${patch.decision}`}
      aside={<span className="truncate pt-0.5 text-[12px] text-muted">{patch.image}</span>}
      className={`transition-opacity ${query.isPlaceholderData ? "opacity-60" : ""}`}
    >
      <Strip patch={patch} truth={truth} />
      <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] text-ink2" aria-label="Chú thích màu box">
        {legend.map(({ key, label }) => (
          <li key={key} className="inline-flex items-center gap-2">
            <span
              aria-hidden
              className="size-3 rounded-[3px] border-2"
              style={{ borderColor: COLORS[key], boxShadow: "0 0 0 1px rgb(0 0 0 / 0.25)" }}
            />
            {label}
          </li>
        ))}
      </ul>
      {patch.comment && (
        <p className="mt-4 border-t border-line pt-4 text-[14px] leading-relaxed text-ink">
          <span className="font-semibold">Reviewer {patch.reviewer}:</span> {patch.comment}
        </p>
      )}
    </Panel>
  );
}

export function PatchViewer() {
  const { sp, update } = useView();
  const [truth, setTruth] = useState(false);
  const params = apiParams(sp);
  const query = useQuery({
    queryKey: ["patches", params.toString()],
    queryFn: () => apiGet<PatchList>("/patches", params),
    placeholderData: keepPreviousData,
  });

  // Phần phân tích phía trên đã báo trang chưa có dữ liệu hoặc trống: không nhắc lại.
  if (query.data && "hidden" in query.data) return null;

  const heading = (
    <header>
      <h2 className="text-[20px] font-semibold tracking-[-0.01em]">Xem một bản vá</h2>
      <p className="mt-1.5 max-w-[46em] text-[14px] leading-relaxed text-ink2">
        Ba ảnh cắt cùng một vùng: box annotator đã nộp, box agent đề xuất và box sau khi người duyệt áp dụng.
      </p>
    </header>
  );
  const body = () => {
    if (query.isPending) return <Skeleton className="h-[480px]" />;
    if (query.isError) return <ErrorState error={query.error} />;
    const list = query.data;
    if ("hidden" in list) return null;
    if ("pending" in list)
      return <Rows rows={[{ widths: [1], blocks: [{ type: "pending", title: "Ảnh trước và sau", message: list.pending }] }]} />;
    if (list.items.length === 0) return <EmptyState message="Chưa có bản vá nào được người duyệt quyết định." />;

    // Bản vá trên URL không còn trong danh sách (đổi lọc) thì xem bản đầu tiên.
    const chosen = list.items.find((item) => item.id === sp.get("patch")) ?? list.items[0];
    const counted =
      `${list.total.toLocaleString("en-US")} bản vá đã có quyết định` +
      (list.total > list.max_listed ? `; danh sách hiện ${list.max_listed} bản vá đầu` : "");
    return (
      <>
        <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
          <label className="block w-full max-w-xl min-w-0">
            <span className="mb-1.5 block text-[12px] font-medium text-muted">Bản vá</span>
            <select
              value={chosen.id}
              onChange={(e) => update((next) => next.set("patch", e.target.value))}
              className="h-9 w-full rounded-lg border border-line-strong bg-surface px-2.5 text-[14px] text-ink focus-visible:border-accent"
            >
              {list.items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.id} · {item.operation} · {item.decision} · {item.class_name}
                </option>
              ))}
            </select>
          </label>
          <span className="flex h-9 items-center" title={list.has_truth ? undefined : "Bảng issues chưa có box đáp án (cột gx1…)"}>
            <Switch label="Hiện đáp án" checked={truth && list.has_truth} onChange={setTruth} disabled={!list.has_truth} />
          </span>
          <p className="ml-auto self-center text-[13px] text-muted">{counted}</p>
        </div>
        <div className={query.isPlaceholderData ? "opacity-60" : ""}>
          <Detail id={chosen.id} truth={truth && list.has_truth} />
        </div>
      </>
    );
  };

  return (
    <section className="mt-10 flex flex-col gap-4" aria-label="Xem một bản vá">
      {heading}
      {body()}
    </section>
  );
}
