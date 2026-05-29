import { useEffect, useMemo, useState } from "react";
import { AlertCircle, FileText, Filter, FolderClosed, LayoutList, Search } from "lucide-react";
import { adminApi, type AdminDocument, type AdminDocumentOverview } from "../lib/api";
import { formatDateTime, scopeLabel } from "../lib/format";

const fallbackOverview: AdminDocumentOverview = {
  metrics: [],
  items: [],
};

function documentStatus(document: AdminDocument) {
  return document.is_published
    ? "bg-[#10B981]/10 text-[#10B981]"
    : "bg-surface-variant text-on-surface-variant";
}

export function Documents() {
  const [overview, setOverview] = useState<AdminDocumentOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminApi
      .getDocumentsOverview()
      .then((response) => {
        if (isMounted) {
          setOverview(response);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Không thể tải danh sách tài liệu.");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const filteredDocuments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((document) => {
      const matchesScope = scope === "all" || document.scope === scope;
      const matchesQuery =
        !normalizedQuery ||
        document.title.toLowerCase().includes(normalizedQuery) ||
        (document.classroom_name || "").toLowerCase().includes(normalizedQuery) ||
        (document.teacher_name || "").toLowerCase().includes(normalizedQuery);
      return matchesScope && matchesQuery;
    });
  }, [overview.items, query, scope]);

  const scopeCounts = useMemo(() => {
    return overview.items.reduce(
      (acc, document) => {
        if (document.scope === "class") {
          acc.class += 1;
        } else {
          acc.system += 1;
        }
        return acc;
      },
      { system: 0, class: 0 },
    );
  }, [overview.items]);

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6 h-[calc(100vh-4rem)]">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shrink-0">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Tài liệu</h1>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#F59E0B]/40 bg-[#F59E0B]/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {overview.metrics.map((metric) => (
          <div key={metric.key} className="bg-surface-container-lowest rounded-xl border border-surface-variant shadow-(--shadow-level-1) p-5">
            <p className="text-sm text-outline">{metric.label}</p>
            <p className="text-2xl font-bold text-on-surface mt-2">{metric.value.toLocaleString("vi-VN")}</p>
            <p className="text-xs text-outline mt-1">{metric.subtext}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
        <div className="w-full md:w-64 flex flex-col shrink-0">
          <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant flex-1 overflow-y-auto">
            <div className="p-4 border-b border-surface-variant bg-surface-container-lowest">
              <h3 className="font-bold text-on-surface">Thư mục</h3>
            </div>
            <div className="p-2 space-y-1">
              <button
                onClick={() => setScope("all")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "all" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3"><FolderClosed className="w-4 h-4" /> Tất cả tài liệu</span>
                <span>{overview.items.length}</span>
              </button>
              <button
                onClick={() => setScope("system")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "system" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3"><FolderClosed className="w-4 h-4" /> Hệ thống</span>
                <span>{scopeCounts.system}</span>
              </button>
              <button
                onClick={() => setScope("class")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "class" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3"><FolderClosed className="w-4 h-4" /> Trong lớp</span>
                <span>{scopeCounts.class}</span>
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant flex flex-col min-h-0 overflow-hidden">
          <div className="p-4 border-b border-surface-variant flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-surface-container-lowest">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-bold text-on-surface">{scope === "all" ? "Tất cả tài liệu" : scopeLabel(scope)}</span>
              <span className="text-outline">/</span>
              <span className="text-outline">{filteredDocuments.length} mục</span>
            </div>
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <div className="relative flex-1 sm:w-72">
                <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Tìm kiếm tài liệu..."
                  className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                />
              </div>
              <button className="p-2 border border-outline-variant rounded-md text-outline hover:bg-surface-container-low transition-colors">
                <Filter className="w-4 h-4" />
              </button>
              <div className="flex rounded-md p-1 bg-surface-container-low">
                <button className="p-1.5 bg-surface-container-lowest shadow-sm rounded text-primary"><LayoutList className="w-4 h-4" /></button>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-left border-collapse min-w-212.5">
              <thead className="bg-surface-container-lowest sticky top-0 z-10 border-b border-surface-variant">
                <tr>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Tên</th>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Scope</th>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Lớp</th>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Người tạo</th>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Sửa đổi</th>
                  <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Trạng thái</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-variant">
                {filteredDocuments.map((document) => (
                  <tr key={document.id} className="hover:bg-surface-container-low/50 transition-colors cursor-pointer">
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div className="flex flex-col gap-0.5">
                          <p className="text-sm font-semibold text-on-surface leading-tight">{document.title}</p>
                          <p className="text-xs text-outline max-w-80 truncate">{document.content_preview || "Không có mô tả"}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-sm text-on-surface">{scopeLabel(document.scope)}</td>
                    <td className="py-3 px-4 text-sm text-on-surface">{document.classroom_name || "Không gắn lớp"}</td>
                    <td className="py-3 px-4 text-sm text-on-surface">{document.teacher_name || "Chưa xác định"}</td>
                    <td className="py-3 px-4 text-sm text-on-surface">{formatDateTime(document.updated_at)}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-block px-3 py-1 text-xs font-bold rounded-full ${documentStatus(document)}`}>
                        {document.is_published ? "Đã xuất bản" : "Bản nháp"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!isLoading && filteredDocuments.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-sm text-outline">Chưa có tài liệu phù hợp.</td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-sm text-outline">Đang tải dữ liệu tài liệu...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="p-4 border-t border-surface-variant text-sm text-outline bg-surface-container-lowest">
            Đang hiển thị {filteredDocuments.length} trong số {overview.items.length} tài liệu
          </div>
        </div>
      </div>
    </div>
  );
}
