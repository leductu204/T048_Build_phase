// Khung trang: thanh bên có danh mục trang và chế độ sáng/tối, dải cảnh báo số giả ở đầu vùng nội dung.
// Trên điện thoại thanh bên thành ngăn kéo.
import { Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router";
import type { Meta } from "../lib/api";
import { PageIcon } from "../lib/icons";
import { useTheme } from "../lib/theme";
import { sharedSearch, useView } from "../lib/view";
import { Segmented } from "./ui";

/** Dấu của sản phẩm: khung chọn bốn góc ôm một box, như khi soi một vật trong CVAT. */
function Mark() {
  return (
    <svg viewBox="0 0 28 28" aria-hidden className="size-7 shrink-0">
      <path d="M2 9V2h7M19 2h7v7M26 19v7h-7M9 26H2v-7" fill="none" stroke="var(--accent)" strokeWidth="2.5" />
      <rect x="8" y="9.5" width="12" height="9" rx="1.5" fill="var(--ink)" />
    </svg>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <Mark />
      <div className="leading-tight">
        <p className="text-[15px] font-semibold tracking-tight">M22</p>
        <p className="text-[12px] text-muted">Issue analytics cho CVAT</p>
      </div>
    </div>
  );
}

/** Chọn bộ dữ liệu. Đổi bộ thì bỏ lựa chọn chỉ đúng với bộ cũ (annotator, issue và bản vá đang xem). */
function DatasetPicker({ meta }: { meta: Meta }) {
  const { update } = useView();
  if (meta.datasets.length === 0) return null;
  const choose = (name: string) =>
    update((next) => {
      if (name) next.set("ds", name);
      else next.delete("ds");
      next.delete("annotator");
      next.delete("issue");
      next.delete("patch");
    });
  return (
    <label className="block shrink-0 px-5 pb-3">
      <span className="mb-1.5 block text-[12px] font-medium text-muted">Bộ dữ liệu</span>
      <select
        value={meta.dataset}
        onChange={(e) => choose(e.target.value)}
        className="h-9 w-full rounded-lg border border-line-strong bg-surface px-2.5 text-[14px] text-ink focus-visible:border-accent"
      >
        <option value="">Mặc định</option>
        {meta.datasets.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

function Sidebar({ meta, onClose }: { meta: Meta; onClose?: () => void }) {
  const { sp } = useView();
  const { dark, setDark } = useTheme();
  const search = sharedSearch(sp);
  const unported = meta.sections.some((s) => s.pages.some((p) => !p.ported));
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 shrink-0 items-center justify-between px-5">
        <Brand />
        {onClose && (
          <button type="button" aria-label="Đóng danh mục" onClick={onClose} className="rounded-md p-1.5 text-ink2 hover:bg-soft">
            <X aria-hidden className="size-5" />
          </button>
        )}
      </div>
      <DatasetPicker meta={meta} />
      <nav aria-label="Các trang" className="flex-1 overflow-y-auto px-3 pt-1 pb-5 [scrollbar-width:thin]">
        {meta.sections.map((section) => (
          <div key={section.title} className="mt-4 first:mt-1">
            <p className="px-2.5 pb-1.5 text-[12px] font-medium text-muted">{section.title}</p>
            <ul className="flex flex-col gap-px">
              {section.pages.map((p) => (
                <li key={p.path}>
                  <NavLink
                    to={{ pathname: `/${p.path}`, search }}
                    title={p.ported ? undefined : "Chưa chuyển sang bản mới. Xem ở bản Streamlit."}
                    className={({ isActive }) =>
                      `flex h-8 items-center gap-2.5 rounded-md px-2.5 text-[14px] transition-colors ${
                        isActive
                          ? "bracketed bg-soft font-medium text-ink [--bracket-size:7px]"
                          : p.ported
                            ? "text-ink2 hover:bg-soft/70 hover:text-ink"
                            : "text-muted hover:bg-soft/70 hover:text-ink2"
                      }`
                    }
                  >
                    <PageIcon name={p.icon} />
                    <span className="min-w-0 flex-1 truncate">{p.title}</span>
                    {!p.ported && <span aria-label="chưa chuyển" className="size-1.5 shrink-0 rounded-full border border-muted" />}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {unported && (
          <p className="mt-4 flex items-center gap-2 px-2.5 text-[12px] text-muted">
            <span className="size-1.5 shrink-0 rounded-full border border-muted" />
            Chưa chuyển sang bản mới
          </p>
        )}
      </nav>
      <div className="shrink-0 border-t border-line px-5 py-4">
        <Segmented
          label="Chế độ hiển thị"
          value={dark ? "dark" : "light"}
          onChange={(v) => setDark(v === "dark")}
          options={[
            { value: "light", label: "Sáng", icon: Sun },
            { value: "dark", label: "Tối", icon: Moon },
          ]}
        />
      </div>
    </div>
  );
}

/** Không ai được nhầm số giả là số thật: dải sọc chạy ngang mọi trang khi đang xem số giả. */
function MockBand({ meta }: { meta: Meta }) {
  const { demo } = useView();
  if (meta.mode !== "mock") return null;
  return (
    <div role="status" className="flex items-stretch border-b border-mock/30 bg-mock-soft text-[13px] text-mock-ink">
      <span aria-hidden className="hatch w-10 shrink-0 opacity-70 sm:w-14" />
      <p className="px-4 py-2.5 leading-snug">
        {demo
          ? "Đang xem số giả theo lựa chọn của bạn; các file thật đang bị bỏ qua."
          : "Đang xem số giả, sinh từ bộ đáp án để xem trước giao diện. Không trích các số này vào báo cáo."}
      </p>
    </div>
  );
}

export function Layout({ meta, children }: { meta: Meta; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/95 px-4 backdrop-blur lg:hidden">
        <button
          type="button"
          aria-label="Mở danh mục trang"
          aria-expanded={open}
          onClick={() => setOpen(true)}
          className="-ml-1 rounded-md p-1.5 text-ink2 hover:bg-soft"
        >
          <Menu aria-hidden className="size-5" />
        </button>
        <Brand />
      </header>
      {open && <div aria-hidden className="fixed inset-0 z-40 bg-black/45 lg:hidden" onClick={() => setOpen(false)} />}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 border-r border-line bg-surface transition-transform duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <Sidebar meta={meta} onClose={open ? () => setOpen(false) : undefined} />
      </aside>
      <main className="lg:pl-64">
        <MockBand meta={meta} />
        <div className="mx-auto max-w-[1440px] px-4 pt-6 pb-16 sm:px-6 lg:px-10 lg:pt-8">{children}</div>
      </main>
    </div>
  );
}
