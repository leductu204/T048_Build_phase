import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useEffect, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation, useParams } from "react-router";
import { FilterBar } from "./components/FilterBar";
import { Layout } from "./components/Layout";
import { PageBoundary } from "./components/PageBoundary";
import { PageHeader } from "./components/PageHeader";
import { ErrorState } from "./components/ui";
import { ApiError, apiGet, type Meta } from "./lib/api";
import { ThemeProvider } from "./lib/theme";
import { sourceParams, useView } from "./lib/view";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { DataStatusPage } from "./pages/DataStatusPage";
import { IssueDetailPage } from "./pages/IssueDetailPage";
import { NotPortedPage } from "./pages/NotPortedPage";
import { PatchViewer } from "./pages/PatchViewer";

const HOME = "tong-quan";
// Trang tra cứu có giao diện riêng; mọi trang khác vẽ bằng khối chung.
const CUSTOM: Record<string, ComponentType> = {
  "chi-tiet-issue": IssueDetailPage,
  "nguon-du-lieu": DataStatusPage,
};
// Phần tương tác vẽ thêm dưới các khối chung của trang phân tích.
const EXTRA: Record<string, ComponentType> = {
  "sua-agent": PatchViewer,
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      // Lỗi do tham số (4xx) thì thử lại cũng vậy.
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 1,
    },
  },
});

function PageRoute({ meta }: { meta: Meta }) {
  const { path } = useParams();
  const { search } = useLocation();
  const page = meta.sections.flatMap((s) => s.pages).find((p) => p.path === path);

  useEffect(() => {
    if (page) document.title = `${page.title} | M22 Issue analytics`;
  }, [page]);

  if (!page) return <Navigate to={{ pathname: `/${HOME}`, search }} replace />;
  const Custom = CUSTOM[page.path];
  const Extra = EXTRA[page.path];
  return (
    <>
      <PageHeader page={page} meta={meta} />
      {/* Không bọc thanh lọc trong thẻ khác: sticky chỉ dính trong phạm vi thẻ cha trực tiếp. */}
      {page.ported && page.filters.length > 0 && <FilterBar page={page} options={meta.options} />}
      <div className="mt-6">
        <PageBoundary key={page.path}>
          {!page.ported ? (
            <NotPortedPage />
          ) : Custom ? (
            <Custom />
          ) : (
            <>
              <AnalyticsPage page={page} />
              {Extra && <Extra />}
            </>
          )}
        </PageBoundary>
      </div>
    </>
  );
}

function Shell() {
  const { sp } = useView();
  const { search } = useLocation();
  const params = sourceParams(sp);
  const meta = useQuery({
    queryKey: ["meta", params.toString()],
    queryFn: () => apiGet<Meta>("/meta", params),
  });

  if (meta.isPending)
    return (
      <div role="status" className="flex min-h-dvh flex-col items-center justify-center gap-2 px-6 text-center">
        <LoaderCircle aria-hidden className="size-6 animate-spin text-accent" />
        <p className="mt-2 font-medium">Đang nạp dữ liệu</p>
        <p className="text-[13px] text-muted">Lần đầu mất vài giây để dựng số giả từ bộ đáp án.</p>
      </div>
    );
  if (meta.isError)
    return (
      <div className="mx-auto max-w-xl px-4 py-20">
        <ErrorState error={meta.error} />
      </div>
    );
  return (
    <Layout meta={meta.data}>
      <Routes>
        <Route path="/" element={<Navigate to={{ pathname: `/${HOME}`, search }} replace />} />
        <Route path="/:path" element={<PageRoute meta={meta.data} />} />
      </Routes>
    </Layout>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Shell />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
