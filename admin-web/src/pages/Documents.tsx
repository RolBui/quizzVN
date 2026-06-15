import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  Download,
  FileText,
  Filter,
  FolderClosed,
  Loader2,
  Search,
  Upload,
  X,
} from "lucide-react";
import {
  adminApi,
  type AdminClass,
  type AdminDocument,
  type AdminDocumentOverview,
} from "../lib/api";
import { useAppNotifications } from "../lib/app-notifications";
import { formatDateTime, scopeLabel } from "../lib/format";
import { PaginationBar } from "../components/PaginationBar";
import { toast } from "react-toastify";

const fallbackOverview: AdminDocumentOverview = {
  metrics: [],
  items: [],
};

const PAGE_SIZE = 7;
type DocumentScope = "all" | "system" | "class";
type UploadDocumentScope = Exclude<DocumentScope, "all">;
type DocumentStatusFilter = "all" | "published" | "draft";
type DocumentSortMode =
  | "updated_desc"
  | "updated_asc"
  | "title_asc"
  | "title_desc";

const DOCUMENT_UPLOAD_ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

async function downloadDocumentFile(item: AdminDocument) {
  if (!item.file_url) {
    return false;
  }

  const response = await fetch(item.file_url);
  if (!response.ok) {
    return false;
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = item.file_name || item.title;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
  return true;
}

function documentStatus(document: AdminDocument) {
  return document.is_published ? "badge-success" : "badge-secondary";
}

export function Documents() {
  const { addNotification } = useAppNotifications();
  const [overview, setOverview] =
    useState<AdminDocumentOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<DocumentScope>("all");
  const [statusFilter, setStatusFilter] =
    useState<DocumentStatusFilter>("all");
  const [sortMode, setSortMode] = useState<DocumentSortMode>("updated_desc");
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pageByScope, setPageByScope] = useState<Record<DocumentScope, number>>(
    {
      all: 1,
      system: 1,
      class: 1,
    },
  );
  const [classes, setClasses] = useState<AdminClass[]>([]);
  const [isClassLoading, setIsClassLoading] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importScope, setImportScope] = useState<UploadDocumentScope>("system");
  const [importClassroomId, setImportClassroomId] = useState("");
  const [importTitle, setImportTitle] = useState("");
  const [importSummary, setImportSummary] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportScope, setExportScope] = useState<UploadDocumentScope>("system");
  const [exportClassroomId, setExportClassroomId] = useState("");
  const [exportDocumentId, setExportDocumentId] = useState("");
  const [exportQuery, setExportQuery] = useState("");

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
          setError(
            err instanceof Error
              ? err.message
              : "Không thể tải danh sách tài liệu.",
          );
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

  useEffect(() => {
    const shouldLoadClasses =
      (isImportOpen && importScope === "class") ||
      (isExportOpen && exportScope === "class");
    if (!shouldLoadClasses || classes.length > 0) {
      return;
    }

    let isMounted = true;
    setIsClassLoading(true);
    adminApi
      .getClassesOverview()
      .then((response) => {
        if (isMounted) {
          setClasses(response.items);
        }
      })
      .catch((err) => {
        if (isMounted) {
          const message =
            err instanceof Error ? err.message : "Không thể tải danh sách lớp.";
          if (isImportOpen) {
            setImportError(message);
          }
          if (isExportOpen) {
            setExportError(message);
          }
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsClassLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [classes.length, exportScope, importScope, isExportOpen, isImportOpen]);

  useEffect(() => {
    if (importScope === "class" && !importClassroomId && classes.length > 0) {
      setImportClassroomId(String(classes[0].id));
    }
  }, [classes, importClassroomId, importScope]);

  useEffect(() => {
    if (exportScope === "class" && !exportClassroomId && classes.length > 0) {
      setExportClassroomId(String(classes[0].id));
    }
  }, [classes, exportClassroomId, exportScope]);

  const filteredDocuments = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const documents = overview.items.filter((document) => {
      const matchesScope = scope === "all" || document.scope === scope;
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "published"
          ? document.is_published
          : !document.is_published);
      const matchesQuery =
        !normalizedQuery ||
        document.title.toLowerCase().includes(normalizedQuery) ||
        (document.classroom_name || "")
          .toLowerCase()
          .includes(normalizedQuery) ||
        (document.teacher_name || "").toLowerCase().includes(normalizedQuery);
      return matchesScope && matchesStatus && matchesQuery;
    });

    return [...documents].sort((first, second) => {
      if (sortMode === "title_asc" || sortMode === "title_desc") {
        const result = first.title.localeCompare(second.title, "vi");
        return sortMode === "title_asc" ? result : -result;
      }

      const firstTime = new Date(first.updated_at).getTime();
      const secondTime = new Date(second.updated_at).getTime();
      return sortMode === "updated_desc"
        ? secondTime - firstTime
        : firstTime - secondTime;
    });
  }, [overview.items, query, scope, sortMode, statusFilter]);

  const exportableDocuments = useMemo(() => {
    const normalizedQuery = exportQuery.trim().toLowerCase();
    return overview.items.filter((item) => {
      if (item.scope !== exportScope) {
        return false;
      }
      if (exportScope === "class") {
        if (String(item.classroom_id ?? "") !== exportClassroomId) {
          return false;
        }
      }
      if (!normalizedQuery) {
        return true;
      }
      return (
        item.title.toLowerCase().includes(normalizedQuery) ||
        (item.file_name || "").toLowerCase().includes(normalizedQuery) ||
        (item.content_preview || "").toLowerCase().includes(normalizedQuery) ||
        (item.classroom_name || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [exportClassroomId, exportQuery, exportScope, overview.items]);

  useEffect(() => {
    if (!isExportOpen) {
      return;
    }
    setExportDocumentId(
      exportableDocuments.length > 0 ? String(exportableDocuments[0].id) : "",
    );
  }, [exportableDocuments, isExportOpen]);

  const currentPage = pageByScope[scope];
  const totalPages = Math.max(
    1,
    Math.ceil(filteredDocuments.length / PAGE_SIZE),
  );
  const paginatedDocuments = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredDocuments.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, filteredDocuments]);

  useEffect(() => {
    setPageByScope({ all: 1, system: 1, class: 1 });
  }, [query, sortMode, statusFilter]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setPageByScope((current) => ({
        ...current,
        [scope]: totalPages,
      }));
    }
  }, [currentPage, scope, totalPages]);

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

  const hasAdvancedFilters =
    statusFilter !== "all" || sortMode !== "updated_desc";

  const resetAdvancedFilters = () => {
    setStatusFilter("all");
    setSortMode("updated_desc");
  };

  const handlePageChange = (page: number) => {
    setPageByScope((current) => ({
      ...current,
      [scope]: page,
    }));
  };

  const handleScopeChange = (nextScope: DocumentScope) => {
    setScope(nextScope);
  };

  const openImportDialog = () => {
    const nextScope: UploadDocumentScope =
      scope === "class" ? "class" : "system";
    setImportScope(nextScope);
    setImportClassroomId("");
    setImportTitle("");
    setImportSummary("");
    setImportFile(null);
    setImportError(null);
    setIsImportOpen(true);
  };

  const closeImportDialog = () => {
    if (isImporting) {
      return;
    }
    setIsImportOpen(false);
    setImportError(null);
  };

  const openExportDialog = () => {
    const nextScope: UploadDocumentScope =
      scope === "class" ? "class" : "system";
    setExportScope(nextScope);
    setExportClassroomId("");
    setExportDocumentId("");
    setExportQuery("");
    setExportError(null);
    setIsExportOpen(true);
  };

  const closeExportDialog = () => {
    if (isExporting) {
      return;
    }
    setIsExportOpen(false);
    setExportError(null);
  };

  const handleExportSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setExportError(null);

    if (exportScope === "class" && !exportClassroomId) {
      const message = "Chọn lớp trước khi xuất tài liệu trong lớp.";
      setExportError(message);
      toast.error(message, { toastId: "document-export-validation" });
      return;
    }

    if (!exportDocumentId) {
      const message = "Chọn tài liệu cần xuất.";
      setExportError(message);
      toast.error(message, { toastId: "document-export-validation" });
      return;
    }

    const selectedDocument = exportableDocuments.find(
      (item) => String(item.id) === exportDocumentId,
    );

    if (!selectedDocument) {
      const message = "Không tìm thấy tài liệu đã chọn.";
      setExportError(message);
      toast.error(message, { toastId: "document-export-error" });
      return;
    }

    try {
      setIsExporting(true);
      const didDownload = await downloadDocumentFile(selectedDocument);
      if (didDownload) {
        addNotification({
          type: "document_export",
          title: "Đã xuất tài liệu",
          body: `${selectedDocument.title} đã được tải về máy.`,
        });
        toast.success("Xuất tài liệu thành công.", {
          toastId: "document-export-success",
        });
      }
      if (!didDownload) {
        const message = "Tài liệu này chưa có file để xuất.";
        setExportError(message);
        toast.error("Xuất tài liệu thất bại.", {
          toastId: "document-export-error",
        });
        return;
      }
      setIsExportOpen(false);
    } catch {
      const message = "Không thể tải file tài liệu về máy.";
      setExportError(message);
      toast.error("Xuất tài liệu thất bại.", {
        toastId: "document-export-error",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setImportError(null);

    if (!importFile) {
      const message = "Chọn file PDF hoặc DOCX trước khi nhập.";
      setImportError(message);
      toast.error(message, { toastId: "document-import-validation" });
      return;
    }

    if (importScope === "class" && !importClassroomId) {
      const message = "Chọn lớp để nhập tài liệu trong lớp.";
      setImportError(message);
      toast.error(message, { toastId: "document-import-validation" });
      return;
    }

    const formData = new FormData();
    formData.append("file", importFile);
    formData.append("scope", importScope);
    formData.append("is_published", "true");

    if (importTitle.trim()) {
      formData.append("title", importTitle.trim());
    }
    if (importSummary.trim()) {
      formData.append("summary", importSummary.trim());
    }
    if (importScope === "class") {
      formData.append("classroom_id", importClassroomId);
    }

    try {
      setIsImporting(true);
      await adminApi.importDocument(formData);
      const response = await adminApi.getDocumentsOverview();
      const importedTitle = importTitle.trim() || importFile.name;
      const importedScope =
        importScope === "class"
          ? `lớp ${
              classes.find((item) => String(item.id) === importClassroomId)
                ?.name || "đã chọn"
            }`
          : "hệ thống";
      setOverview(response);
      setScope(importScope);
      setPageByScope((current) => ({
        ...current,
        all: 1,
        [importScope]: 1,
      }));
      addNotification({
        type: "document_import",
        title: "Đã nhập tài liệu",
        body: `${importedTitle} đã được tải lên ${importedScope}.`,
      });
      toast.success("Nhập tài liệu thành công.", {
        toastId: "document-import-success",
      });
      setIsImportOpen(false);
      setImportTitle("");
      setImportSummary("");
      setImportFile(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Không thể nhập tài liệu.";
      setImportError(message);
      toast.error("Nhập tài liệu thất bại.", {
        toastId: "document-import-error",
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shrink-0">
        <div>
          <h1 className="text-lg md:text-xl font-semibold text-on-surface">
            Quản lý Tài liệu
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={openExportDialog}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-primary px-4 text-sm font-semibold text-primary transition-colors hover:bg-primary/10"
          >
            <Download className="h-4 w-4" />
            Xuất
          </button>
          <button
            type="button"
            onClick={openImportDialog}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary/90"
          >
            <Upload className="h-4 w-4" />
            Nhập
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#F59E0B]/40 bg-[#F59E0B]/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
          {error}
        </div>
      )}

      <div className="flex flex-col md:flex-row items-start gap-4">
        <div className="w-full md:w-64 flex flex-col shrink-0">
          <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant overflow-hidden">
            <div className="p-4 border-b border-surface-variant bg-surface-container-lowest">
              <h3 className="font-bold text-on-surface">Thư mục</h3>
            </div>
            <div className="p-2 space-y-1">
              <button
                onClick={() => handleScopeChange("all")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "all" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3">
                  <FolderClosed className="w-4 h-4" /> Tất cả tài liệu
                </span>
                <span>{overview.items.length}</span>
              </button>
              <button
                onClick={() => handleScopeChange("system")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "system" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3">
                  <FolderClosed className="w-4 h-4" /> Hệ thống
                </span>
                <span>{scopeCounts.system}</span>
              </button>
              <button
                onClick={() => handleScopeChange("class")}
                className={`w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${scope === "class" ? "bg-primary/10 text-primary" : "text-on-surface hover:bg-surface-container-low"}`}
              >
                <span className="flex items-center gap-3">
                  <FolderClosed className="w-4 h-4" /> Trong lớp
                </span>
                <span>{scopeCounts.class}</span>
              </button>
            </div>
          </div>
        </div>

        <div className="w-full flex-1 overflow-visible rounded-xl border border-surface-variant bg-surface-container-lowest shadow-(--shadow-level-1)">
          <div className="p-4 border-b border-surface-variant flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-surface-container-lowest">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-bold text-on-surface">
                {scope === "all" ? "Tất cả tài liệu" : scopeLabel(scope)}
              </span>
              <span className="text-outline">/</span>
              <span className="text-outline">
                {filteredDocuments.length} mục
              </span>
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
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsFilterOpen((current) => !current)}
                  className={`relative p-2 border rounded-md transition-colors ${
                    isFilterOpen || hasAdvancedFilters
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-outline-variant text-outline hover:bg-surface-container-low"
                  }`}
                  aria-label="Bộ lọc tài liệu"
                >
                  <Filter className="w-4 h-4" />
                  {hasAdvancedFilters && (
                    <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-primary" />
                  )}
                </button>

                {isFilterOpen && (
                  <div className="absolute right-0 top-11 z-50 w-72 rounded-xl border border-outline-variant bg-surface-container-lowest p-3 shadow-(--shadow-level-2)">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <p className="text-sm font-bold text-on-surface">
                        Bộ lọc tài liệu
                      </p>
                      <button
                        type="button"
                        onClick={resetAdvancedFilters}
                        disabled={!hasAdvancedFilters}
                        className="text-xs font-semibold text-primary disabled:text-outline disabled:opacity-60"
                      >
                        Đặt lại
                      </button>
                    </div>

                    <div className="space-y-3">
                      <label className="flex flex-col gap-1.5 text-xs font-semibold text-on-surface">
                        Trạng thái
                        <div className="relative">
                          <select
                            value={statusFilter}
                            onChange={(event) => {
                              setStatusFilter(
                                event.target.value as DocumentStatusFilter,
                              );
                              setIsFilterOpen(false);
                            }}
                            className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-low px-3 pr-10 text-sm font-medium text-on-surface outline-none"
                          >
                            <option value="all">Tất cả trạng thái</option>
                            <option value="published">Đã xuất bản</option>
                            <option value="draft">Bản nháp</option>
                          </select>
                          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                        </div>
                      </label>

                      <label className="flex flex-col gap-1.5 text-xs font-semibold text-on-surface">
                        Sắp xếp
                        <div className="relative">
                          <select
                            value={sortMode}
                            onChange={(event) => {
                              setSortMode(
                                event.target.value as DocumentSortMode,
                              );
                              setIsFilterOpen(false);
                            }}
                            className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-low px-3 pr-10 text-sm font-medium text-on-surface outline-none"
                          >
                            <option value="updated_desc">Mới cập nhật trước</option>
                            <option value="updated_asc">Cũ cập nhật trước</option>
                            <option value="title_asc">Tên A-Z</option>
                            <option value="title_desc">Tên Z-A</option>
                          </select>
                          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                        </div>
                      </label>
                    </div>

                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] table-fixed text-left border-collapse">
              <thead className="bg-surface-container-lowest sticky top-0 z-10 border-b border-surface-variant">
                <tr>
                  <th className="w-[28%] py-3 px-4 text-xs font-bold text-on-surface tracking-wider">
                    Tên
                  </th>
                  <th className="w-[10%] py-3 px-3 text-xs font-bold text-on-surface tracking-wider">
                    Phân loại
                  </th>
                  <th className="w-[13%] py-3 px-3 text-xs font-bold text-on-surface tracking-wider">
                    Lớp
                  </th>
                  <th className="w-[16%] py-3 px-3 text-xs font-bold text-on-surface tracking-wider">
                    Người tạo
                  </th>
                  <th className="w-[18%] py-3 px-3 text-xs font-bold text-on-surface tracking-wider">
                    Sửa đổi
                  </th>
                  <th className="w-[15%] py-3 px-3 text-xs font-bold text-on-surface tracking-wider">
                    Trạng thái
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-variant">
                {paginatedDocuments.map((document) => (
                  <tr
                    key={document.id}
                    className="hover:bg-surface-container-low/50 transition-colors cursor-pointer"
                  >
                    <td className="py-4 px-4">
                      <div className="flex min-w-0 items-center gap-3">
                        <div className="w-10 h-10 shrink-0 rounded-lg bg-surface-container flex items-center justify-center text-primary">
                          <FileText className="w-5 h-5" />
                        </div>
                        <div className="flex min-w-0 flex-col gap-0.5">
                          <p className="truncate text-sm font-semibold text-on-surface leading-tight">
                            {document.title}
                          </p>
                          <p className="truncate text-xs text-outline">
                            {document.content_preview || "Không có mô tả"}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-sm text-on-surface whitespace-nowrap">
                      {scopeLabel(document.scope)}
                    </td>
                    <td className="py-3 px-3 text-sm text-on-surface max-w-0 truncate whitespace-nowrap">
                      {document.classroom_name || "Không gắn lớp"}
                    </td>
                    <td className="py-3 px-3 text-sm text-on-surface max-w-0 truncate whitespace-nowrap">
                      {document.teacher_name || "Chưa xác định"}
                    </td>
                    <td className="py-3 px-3 text-sm text-on-surface whitespace-nowrap">
                      {formatDateTime(document.updated_at)}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      <span
                        className={`badge ${documentStatus(document)}`}
                      >
                        {document.is_published ? "Đã xuất bản" : "Bản nháp"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!isLoading && filteredDocuments.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="py-10 text-center text-sm text-outline"
                    >
                      Chưa có tài liệu phù hợp.
                    </td>
                  </tr>
                )}
                {isLoading && (
                  <tr>
                    <td
                      colSpan={6}
                      className="py-10 text-center text-sm text-outline"
                    >
                      Đang tải dữ liệu tài liệu...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <PaginationBar
            page={currentPage}
            pageSize={PAGE_SIZE}
            totalItems={filteredDocuments.length}
            onPageChange={handlePageChange}
          />
        </div>
      </div>

      {isExportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="w-full max-w-lg overflow-hidden rounded-xl border border-surface-variant bg-surface-container-lowest shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-surface-variant px-5 py-3.5">
              <div>
                <h2 className="text-lg font-bold text-on-surface">
                  Xuất tài liệu
                </h2>
              </div>
              <button
                type="button"
                onClick={closeExportDialog}
                className="rounded-md p-2 text-outline transition-colors hover:bg-surface-container-low hover:text-on-surface"
                aria-label="Đóng form xuất tài liệu"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form
              onSubmit={handleExportSubmit}
              className="space-y-3 px-5 py-3.5"
            >
              <div className="grid gap-3 sm:grid-cols-[0.8fr_1.2fr]">
                <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                  Phân loại
                  <div className="relative">
                    <select
                      value={exportScope}
                      onChange={(event) => {
                        setExportScope(
                          event.target.value as UploadDocumentScope,
                        );
                        setExportClassroomId("");
                        setExportError(null);
                      }}
                      className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-lowest pl-3 pr-12 text-sm font-medium text-on-surface outline-none transition-colors focus:border-outline-variant focus:ring-0"
                    >
                      <option value="system">Hệ thống</option>
                      <option value="class">Trong lớp</option>
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                  </div>
                </label>

                <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                  Tìm kiếm
                  <div className="relative">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                    <input
                      type="text"
                      value={exportQuery}
                      onChange={(event) => {
                        setExportQuery(event.target.value);
                        setExportError(null);
                      }}
                      placeholder="Tìm tài liệu..."
                      className="h-10 w-full rounded-lg border border-outline-variant bg-surface-container-lowest pl-9 pr-3 text-sm font-medium text-on-surface outline-none transition-colors placeholder:text-outline focus:border-primary focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </label>

                {exportScope === "class" && (
                  <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface sm:col-span-2">
                    Lớp
                    <div className="relative">
                      <select
                        value={exportClassroomId}
                        onChange={(event) => {
                          setExportClassroomId(event.target.value);
                          setExportError(null);
                        }}
                        disabled={isClassLoading || classes.length === 0}
                        className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-lowest pl-3 pr-12 text-sm font-medium text-on-surface outline-none transition-colors focus:border-outline-variant focus:ring-0 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isClassLoading && <option>Đang tải lớp...</option>}
                        {!isClassLoading && classes.length === 0 && (
                          <option>Chưa có lớp</option>
                        )}
                        {!isClassLoading &&
                          classes.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.name}
                            </option>
                          ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                    </div>
                  </label>
                )}
              </div>

              <div className="flex flex-col gap-2">
                <span className="flex items-center gap-2 text-sm font-semibold text-on-surface">
                  Tài liệu
                  <span className="text-xs font-medium text-outline">
                    / {exportableDocuments.length} mục
                  </span>
                </span>
                <div className="max-h-56 overflow-y-auto rounded-lg border border-outline-variant bg-surface-container-lowest">
                  {exportableDocuments.length > 0 ? (
                    exportableDocuments.map((item) => (
                      <label
                        key={item.id}
                        className={`flex cursor-pointer items-start gap-2.5 border-b border-surface-variant px-3 py-2.5 last:border-b-0 transition-colors hover:bg-surface-container-low ${
                          exportDocumentId === String(item.id)
                            ? "bg-primary/10"
                            : ""
                        }`}
                      >
                        <input
                          type="radio"
                          name="export_document_id"
                          value={item.id}
                          checked={exportDocumentId === String(item.id)}
                          onChange={(event) => {
                            setExportDocumentId(event.target.value);
                            setExportError(null);
                          }}
                          className="mt-1 h-4 w-4 accent-primary"
                        />
                        <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-semibold text-on-surface">
                            {item.title}
                          </span>
                          <span className="block truncate text-xs text-outline">
                            {item.file_name ||
                              item.content_preview ||
                              "Chưa có file"}
                          </span>
                        </span>
                      </label>
                    ))
                  ) : (
                    <div className="px-3 py-8 text-center text-sm text-outline">
                      {exportQuery.trim()
                        ? "Không tìm thấy tài liệu phù hợp."
                        : "Chưa có tài liệu phù hợp để xuất."}
                    </div>
                  )}
                </div>
              </div>

              {exportError && (
                <div className="flex items-center gap-2 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 px-3 py-2 text-sm text-[#B91C1C]">
                  <AlertCircle className="h-4 w-4" />
                  {exportError}
                </div>
              )}

              <div className="flex justify-end gap-3 border-t border-surface-variant pt-3">
                <button
                  type="button"
                  onClick={closeExportDialog}
                  className="h-10 rounded-lg border border-outline-variant px-4 text-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-low"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={
                    isExporting ||
                    !exportDocumentId ||
                    (exportScope === "class" &&
                      (isClassLoading || !exportClassroomId))
                  }
                  className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isExporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  Xuất
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isImportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
          <div className="w-full max-w-xl overflow-hidden rounded-xl border border-surface-variant bg-surface-container-lowest shadow-xl">
            <div className="flex items-start justify-between gap-4 border-b border-surface-variant px-5 py-4">
              <div>
                <h2 className="text-lg font-bold text-on-surface">
                  Nhập tài liệu
                </h2>
                <p className="mt-1 text-sm text-outline">
                  Chọn phân loại và tải file PDF hoặc DOCX lên hệ thống.
                </p>
              </div>
              <button
                type="button"
                onClick={closeImportDialog}
                className="rounded-md p-2 text-outline transition-colors hover:bg-surface-container-low hover:text-on-surface"
                aria-label="Đóng form nhập tài liệu"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleImportSubmit} className="space-y-4 px-5 py-4">
              <div className="grid gap-4 sm:grid-cols-[14rem_minmax(0,1fr)]">
                <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                  Phân loại
                  <div className="relative">
                    <select
                      value={importScope}
                      onChange={(event) =>
                        setImportScope(
                          event.target.value as UploadDocumentScope,
                        )
                      }
                      className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-lowest pl-3 pr-12 text-sm font-medium text-on-surface outline-none transition-colors focus:border-outline-variant focus:ring-0"
                    >
                      <option value="system">Hệ thống</option>
                      <option value="class">Trong lớp</option>
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                  </div>
                </label>

                {importScope === "class" && (
                  <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                    Lớp
                    <div className="relative">
                      <select
                        value={importClassroomId}
                        onChange={(event) =>
                          setImportClassroomId(event.target.value)
                        }
                        disabled={isClassLoading || classes.length === 0}
                        className="h-10 w-full appearance-none rounded-lg border border-outline-variant bg-surface-container-lowest pl-3 pr-12 text-sm font-medium text-on-surface outline-none transition-colors focus:border-outline-variant focus:ring-0 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isClassLoading && <option>Đang tải lớp...</option>}
                        {!isClassLoading && classes.length === 0 && (
                          <option>Chưa có lớp</option>
                        )}
                        {!isClassLoading &&
                          classes.map((item) => (
                            <option key={item.id} value={item.id}>
                              {item.name}
                            </option>
                          ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                    </div>
                  </label>
                )}
              </div>

              <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                Tên tài liệu
                <input
                  type="text"
                  value={importTitle}
                  onChange={(event) => setImportTitle(event.target.value)}
                  placeholder="Để trống sẽ dùng tên file"
                  className="h-10 rounded-lg border border-outline-variant bg-surface-container-lowest px-3 text-sm font-medium text-on-surface outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                Mô tả ngắn
                <textarea
                  value={importSummary}
                  onChange={(event) => setImportSummary(event.target.value)}
                  placeholder="Mô tả ngắn cho tài liệu"
                  rows={3}
                  className="resize-none rounded-lg border border-outline-variant bg-surface-container-lowest px-3 py-2 text-sm font-medium text-on-surface outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-2 text-sm font-semibold text-on-surface">
                File tài liệu
                <input
                  type="file"
                  accept={DOCUMENT_UPLOAD_ACCEPT}
                  onChange={(event) =>
                    setImportFile(event.target.files?.[0] ?? null)
                  }
                  className="block w-full rounded-lg border border-dashed border-outline-variant bg-surface-container-low px-3 py-3 text-sm text-outline file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-2 file:text-sm file:font-semibold file:text-on-primary"
                />
              </label>

              {importError && (
                <div className="flex items-center gap-2 rounded-lg border border-[#EF4444]/30 bg-[#EF4444]/10 px-3 py-2 text-sm text-[#B91C1C]">
                  <AlertCircle className="h-4 w-4" />
                  {importError}
                </div>
              )}

              <div className="flex justify-end gap-3 border-t border-surface-variant pt-4">
                <button
                  type="button"
                  onClick={closeImportDialog}
                  className="h-10 rounded-lg border border-outline-variant px-4 text-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-low"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={
                    isImporting ||
                    (importScope === "class" &&
                      (isClassLoading || !importClassroomId))
                  }
                  className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 text-sm font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isImporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Upload className="h-4 w-4" />
                  )}
                  Nhập
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
