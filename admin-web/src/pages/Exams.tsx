import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import {
  AlertCircle,
  ChevronDown,
  Loader2,
  Plus,
  Search,
  Trash2,
  X,
  MoreVertical,
  Eye,
  Pencil,
  Globe,
  EyeOff,
} from "lucide-react";
import { adminApi, type AdminExam, type AdminExamOverview } from "../lib/api";
import { PaginationBar } from "../components/PaginationBar";
import { ExamDetailModal } from "../components/ExamDetailModal";
import {
  formatDateTime,
  formatDecimal,
  formatNumber,
  scopeLabel,
} from "../lib/format";

const fallbackOverview: AdminExamOverview = {
  metrics: [],
  items: [],
  total: 0,
  limit: null,
  offset: 0,
};

const PAGE_SIZE = 7;

const renderStatusBadge = (exam: AdminExam) => {
  if (!exam.is_published && !exam.is_active) {
    return <span className="badge badge-warning">Bản nháp</span>;
  }
  if (exam.is_published && exam.is_active) {
    return <span className="badge badge-success">Công khai</span>;
  }
  if (!exam.is_published && exam.is_active) {
    return <span className="badge badge-warning">Riêng tư</span>;
  }
  return <span className="badge badge-info">Không công khai</span>;
};

export function Exams() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<AdminExamOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingExam, setDeletingExam] = useState<AdminExam | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [activeDropdownExamId, setActiveDropdownExamId] = useState<number | null>(null);
  const [selectedExam, setSelectedExam] = useState<AdminExam | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  useEffect(() => {
    const handleOutsideClick = () => {
      setActiveDropdownExamId(null);
    };
    window.addEventListener("click", handleOutsideClick);
    return () => {
      window.removeEventListener("click", handleOutsideClick);
    };
  }, []);

  const handleToggleVisibility = async (exam: AdminExam) => {
    setActiveDropdownExamId(null);
    try {
      if (exam.is_published) {
        await adminApi.privateExam(exam.id);
        toast.success("Đã ẩn đề thi.");
      } else {
        await adminApi.publishExam(exam.id);
        toast.success("Đã xuất bản đề thi.");
      }
      const response = await adminApi.getExamsOverview();
      setOverview(response);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Thao tác thất bại.");
    }
  };

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminApi
      .getExamsOverview()
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
              : "Không thể tải danh sách bài thi.",
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

  const closeDeleteModal = () => {
    if (isDeleting) {
      return;
    }
    setDeletingExam(null);
    setDeleteError(null);
  };

  const handleDeleteExam = async () => {
    if (!deletingExam) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);
    try {
      await adminApi.deleteExam(deletingExam.id);
      const response = await adminApi.getExamsOverview();
      setOverview(response);
      setDeletingExam(null);
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Không xóa được bài thi.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredExams = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((exam) => {
      const matchesSource =
        sourceFilter === "all" || exam.source === sourceFilter;
      const matchesQuery =
        !normalizedQuery ||
        exam.title.toLowerCase().includes(normalizedQuery) ||
        (exam.classroom_name || "").toLowerCase().includes(normalizedQuery) ||
        (exam.teacher_name || "").toLowerCase().includes(normalizedQuery);
      return matchesSource && matchesQuery;
    });
  }, [overview.items, query, sourceFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredExams.length / PAGE_SIZE));

  const paginatedExams = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredExams.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, filteredExams]);

  useEffect(() => {
    setCurrentPage(1);
  }, [query, sourceFilter]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const totalExamCount = overview.total || overview.items.length;
  const submittedMetric = overview.metrics.find(
    (metric) => metric.key === "submitted_attempts",
  );
  const activeMetric = overview.metrics.find(
    (metric) => metric.key === "active_exams",
  );

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-lg  font-semibold text-on-surface">
            Quản lý Bài thi
          </h1>
        </div>
        <button
          type="button"
          onClick={() => navigate("/exams/new")}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary shadow-sm transition-colors hover:bg-primary/90 sm:w-auto"
        >
          <Plus className="w-4 h-4" />
          Tạo đề thi
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-outline-variant flex flex-col items-start">
          <div>
            <p className="text-sm text-on-surface font-medium">Tổng đề thi</p>
          </div>
          <p className="text-3xl font-bold text-on-surface mt-1">
            {formatNumber(totalExamCount)}
          </p>
          <p className="text-xs text-on-surface mt-2">bài thi trong hệ thống</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-outline-variant flex flex-col items-start">
          <div>
            <p className="text-sm text-on-surface font-medium">
              {submittedMetric?.label || "Lượt hoàn thành"}
            </p>
          </div>
          <p className="text-3xl font-bold text-on-surface mt-1">
            {formatNumber(submittedMetric?.value)}
          </p>
          <p className="text-xs text-on-surface mt-2">
            {submittedMetric?.subtext || "bài làm đã nộp"}
          </p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-outline-variant flex flex-col items-start">
          <div>
            <p className="text-sm text-on-surface font-medium">
              {activeMetric?.label || "Bài thi đang mở"}
            </p>
          </div>
          <p className="text-3xl font-bold text-on-surface mt-1">
            {formatNumber(activeMetric?.value)}
          </p>
          <p className="text-xs text-on-surface-variant mt-2">
            {activeMetric?.subtext || "đã xuất bản và hoạt động"}
          </p>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-outline-variant overflow-hidden">
        <div className="p-4 border-b border-surface-variant bg-surface-container-lowest">
          <div className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative w-full md:w-96">
              <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Tìm bài thi, lớp hoặc giáo viên..."
                className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none placeholder:text-outline"
              />
            </div>
            <div className="relative w-full sm:w-32">
              <select
                value={sourceFilter}
                onChange={(event) => setSourceFilter(event.target.value)}
                className="w-full appearance-none bg-surface-container-low border border-outline-variant text-sm py-2 pl-3 pr-8 rounded-lg focus:outline-none focus:border-primary cursor-pointer text-on-surface"
              >
                <option value="all">Tất cả</option>
                <option value="system">Hệ thống</option>
                <option value="teacher">Giáo viên</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] table-fixed text-left border-collapse">
            <thead className="bg-surface-container-lowest border-b border-surface-variant">
              <tr className="border-b border-surface-variant bg-surface-container-lowest text-outline">
                <th className="w-[22%] py-3 px-4 text-xs text-on-surface font-bold whitespace-nowrap">
                  Tên bài thi
                </th>
                <th className="w-[10%] py-3 px-3 text-xs text-on-surface font-bold whitespace-nowrap">
                  Phân loại
                </th>
                <th className="w-[14%] py-3 px-3 text-xs text-on-surface font-bold whitespace-nowrap">
                  Giáo viên
                </th>
                <th className="w-[8%] py-3 px-3 text-xs text-on-surface-variant font-bold text-center whitespace-nowrap">
                  Câu hỏi
                </th>
                <th className="w-[8%] py-3 px-3 text-xs text-on-surface font-bold text-center whitespace-nowrap">
                  Lượt làm
                </th>
                <th className="w-[10%] py-3 px-3 text-xs text-on-surface font-bold whitespace-nowrap">
                  Điểm TB
                </th>
                <th className="w-[12%] py-3 px-3 text-xs text-on-surface font-bold whitespace-nowrap">
                  Ngày tạo
                </th>
                <th className="w-[10%] py-3 px-3 text-xs text-on-surface font-bold whitespace-nowrap">
                  Trạng thái
                </th>
                <th className="w-[6%] py-3 px-3 text-xs text-on-surface font-bold text-center whitespace-nowrap">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/70">
              {paginatedExams.map((exam) => (
                <tr
                  key={exam.id}
                  className="hover:bg-surface-container-low/50 transition-colors bg-surface-container-lowest"
                >
                  <td className="py-4 px-4">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-on-surface">
                        {exam.title}
                      </p>
                      <p className="truncate text-xs text-outline">
                        {exam.classroom_name || "Không gắn lớp"}
                      </p>
                    </div>
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface font-medium whitespace-nowrap">
                    {exam.source === "system" ? "Hệ thống" : "Giáo viên"}
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface max-w-0 truncate whitespace-nowrap">
                    {exam.teacher_name || "Chưa xác định"}
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface text-center whitespace-nowrap">
                    {exam.question_count}
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface text-center whitespace-nowrap">
                    {exam.attempt_count}
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface whitespace-nowrap">
                    {exam.average_score === null
                      ? "Chưa có"
                      : formatDecimal(exam.average_score, "%")}
                  </td>
                  <td className="py-4 px-3 text-sm text-on-surface truncate whitespace-nowrap">
                    {formatDateTime(exam.created_at)}
                  </td>
                  <td className="py-4 px-3 whitespace-nowrap">
                    {renderStatusBadge(exam)}
                  </td>
                  <td className="py-4 px-3 text-center relative whitespace-nowrap">
                    <button
                      type="button"
                      className="text-outline hover:text-on-surface p-2 rounded hover:bg-surface-container-low transition-colors"
                      title="Thao tác"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveDropdownExamId(
                          activeDropdownExamId === exam.id ? null : exam.id
                        );
                      }}
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    
                    {activeDropdownExamId === exam.id && (
                      <div 
                        className="absolute right-4 mt-1 w-44 rounded-lg bg-surface-container-lowest border border-outline-variant shadow-lg z-50 py-1 text-left"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setActiveDropdownExamId(null);
                            setSelectedExam(exam);
                            setIsDetailOpen(true);
                          }}
                          className="w-full px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low flex items-center gap-2"
                        >
                          <Eye className="w-3.5 h-3.5 text-outline" />
                          <span>Xem chi tiết</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setActiveDropdownExamId(null);
                            navigate(`/exams/edit/${exam.id}`);
                          }}
                          className="w-full px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low flex items-center gap-2"
                        >
                          <Pencil className="w-3.5 h-3.5 text-outline" />
                          <span>Chỉnh sửa</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleVisibility(exam)}
                          className="w-full px-3 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low flex items-center gap-2"
                        >
                          {exam.is_published ? (
                            <>
                              <EyeOff className="w-3.5 h-3.5 text-outline" />
                              <span>Tạm ẩn</span>
                            </>
                          ) : (
                            <>
                              <Globe className="w-3.5 h-3.5 text-outline" />
                              <span>Công khai</span>
                            </>
                          )}
                        </button>
                        <div className="border-t border-outline-variant my-1" />
                        <button
                          type="button"
                          onClick={() => {
                            setActiveDropdownExamId(null);
                            setDeletingExam(exam);
                            setDeleteError(null);
                          }}
                          className="w-full px-3 py-2 text-xs font-semibold text-error hover:bg-error-container/20 flex items-center gap-2"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-error" />
                          <span>Xóa đề thi</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {!isLoading && filteredExams.length === 0 && (
                <tr>
                  <td
                    colSpan={9}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Chưa có bài thi phù hợp.
                  </td>
                </tr>
              )}
              {isLoading && (
                <tr>
                  <td
                    colSpan={9}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Đang tải dữ liệu bài thi...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar
          page={currentPage}
          pageSize={PAGE_SIZE}
          totalItems={filteredExams.length}
          onPageChange={setCurrentPage}
        />
      </div>

      {deletingExam && (
        <div className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-md bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-on-surface">
                    Xóa bài thi
                  </h2>
                  <p className="text-sm text-outline mt-1">
                    Bài thi và dữ liệu làm bài liên quan sẽ bị xóa.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeDeleteModal}
                disabled={isDeleting}
                className="p-2 rounded-lg hover:bg-surface-container-low text-outline disabled:opacity-60"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form
              onSubmit={(event) => {
                event.preventDefault();
                void handleDeleteExam();
              }}
              className="p-5 space-y-4"
            >
              <div className="rounded-lg border border-error-container bg-error-container/40 px-4 py-3">
                <p className="text-sm text-on-surface">
                  Bạn có chắc muốn xóa bài thi này?
                </p>
                <p className="text-sm font-semibold text-on-surface mt-2">
                  {deletingExam.title}
                </p>
                <p className="text-xs text-outline mt-1">
                  {deletingExam.classroom_name || "Không gắn lớp"}
                </p>
              </div>

              {deleteError && (
                <div className="rounded-lg border border-error-container bg-error-container/60 px-3 py-2 flex items-start gap-2 text-sm text-on-error-container">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{deleteError}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeDeleteModal}
                  disabled={isDeleting}
                  className="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium text-on-surface hover:bg-surface-container-low disabled:opacity-60"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isDeleting}
                  className="px-4 py-2 rounded-lg bg-error text-on-error text-sm font-semibold hover:bg-error/90 disabled:opacity-70 flex items-center gap-2"
                >
                  {isDeleting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Xóa bài thi
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ExamDetailModal
        exam={selectedExam}
        open={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedExam(null);
        }}
      />
    </div>
  );
}
