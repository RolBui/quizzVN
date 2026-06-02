import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Filter, Loader2, Search, Trash2, X } from "lucide-react";
import { adminApi, type AdminExam, type AdminExamOverview } from "../lib/api";
import { formatDateTime, formatDecimal, formatNumber, scopeLabel } from "../lib/format";

const fallbackOverview: AdminExamOverview = {
  metrics: [],
  items: [],
};

export function Exams() {
  const [overview, setOverview] = useState<AdminExamOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingExam, setDeletingExam] = useState<AdminExam | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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
          setError(err instanceof Error ? err.message : "Không thể tải danh sách bài thi.");
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
      setDeleteError(err instanceof Error ? err.message : "Không xóa được bài thi.");
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredExams = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((exam) => {
      const matchesScope = scope === "all" || exam.scope === scope;
      const matchesQuery =
        !normalizedQuery ||
        exam.title.toLowerCase().includes(normalizedQuery) ||
        (exam.classroom_name || "").toLowerCase().includes(normalizedQuery) ||
        (exam.teacher_name || "").toLowerCase().includes(normalizedQuery);
      return matchesScope && matchesQuery;
    });
  }, [overview.items, query, scope]);

  const totalExamCount = overview.items.length;
  const submittedMetric = overview.metrics.find((metric) => metric.key === "submitted_attempts");
  const activeMetric = overview.metrics.find((metric) => metric.key === "active_exams");

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Bài thi</h1>
        </div>
        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm bài thi, lớp hoặc giáo viên..."
              className="w-full bg-surface-container-lowest border border-surface-variant rounded-lg pl-9 pr-3 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none placeholder:text-outline"
            />
          </div>
          <select
            value={scope}
            onChange={(event) => setScope(event.target.value)}
            className="bg-surface-container-lowest border border-surface-variant text-sm py-2 px-3 rounded-lg focus:outline-none focus:border-primary cursor-pointer text-on-surface"
          >
            <option value="all">Tất cả phạm vi</option>
            <option value="system">Hệ thống</option>
            <option value="class">Trong lớp</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-[#F59E0B]/40 bg-[#F59E0B]/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#F59E0B]" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
            <p className="text-sm font-medium text-outline">Tổng đề thi</p>
          </div>
          <p className="text-3xl font-bold text-on-surface">{formatNumber(totalExamCount)}</p>
          <p className="text-xs text-outline">bài thi trong hệ thống</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
            <p className="text-sm font-medium text-outline">{submittedMetric?.label || "Lượt hoàn thành"}</p>
          </div>
          <p className="text-3xl font-bold text-on-surface">{formatNumber(submittedMetric?.value)}</p>
          <p className="text-xs text-outline">{submittedMetric?.subtext || "bài làm đã nộp"}</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
            <p className="text-sm font-medium text-outline">{activeMetric?.label || "Bài thi đang mở"}</p>
          </div>
          <p className="text-3xl font-bold text-on-surface">{formatNumber(activeMetric?.value)}</p>
          <p className="text-xs text-outline">{activeMetric?.subtext || "đã xuất bản và hoạt động"}</p>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant overflow-hidden">
        <div className="p-5 border-b border-surface-variant flex justify-between items-center bg-surface-container-lowest">
          <h3 className="text-lg font-bold text-on-surface">Bài thi trên hệ thống</h3>
          <Filter className="w-5 h-5 text-outline" />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-left border-collapse min-w-[980px]">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-lowest text-outline">
                <th className="py-4 px-6 text-xs font-semibold w-[26%]">Tên Bài thi</th>
                <th className="py-4 px-6 text-xs font-semibold w-[10%]">Scope</th>
                <th className="py-4 px-6 text-xs font-semibold w-[16%]">Giáo viên</th>
                <th className="py-4 px-6 text-xs font-semibold w-[8%] text-center">Câu hỏi</th>
                <th className="py-4 px-6 text-xs font-semibold w-[8%] text-center">Lượt làm</th>
                <th className="py-4 px-6 text-xs font-semibold w-[10%]">Điểm TB</th>
                <th className="py-4 px-6 text-xs font-semibold w-[16%]">Ngày tạo</th>
                <th className="py-4 px-6 text-xs font-semibold w-[6%] text-center">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {filteredExams.map((exam) => (
                  <tr key={exam.id} className="hover:bg-surface-container-low/50 transition-colors bg-surface-container-lowest">
                    <td className="py-4 px-6">
                      <p className="text-sm font-medium text-primary">{exam.title}</p>
                      <p className="text-xs text-outline">{exam.classroom_name || "Không gắn lớp"}</p>
                    </td>
                    <td className="py-4 px-6 text-sm text-outline font-medium">{scopeLabel(exam.scope)}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.teacher_name || "Chưa xác định"}</td>
                    <td className="py-4 px-6 text-sm text-on-surface text-center">{exam.question_count}</td>
                    <td className="py-4 px-6 text-sm text-on-surface text-center">{exam.attempt_count}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.average_score === null ? "Chưa có" : formatDecimal(exam.average_score, "%")}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{formatDateTime(exam.created_at)}</td>
                    <td className="py-4 px-6 text-center">
                      <button
                        className="text-outline hover:text-error p-2 rounded hover:bg-error-container transition-colors"
                        title="Xóa bài thi"
                        onClick={() => {
                          setDeletingExam(exam);
                          setDeleteError(null);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              {!isLoading && filteredExams.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-sm text-outline">Chưa có bài thi phù hợp.</td>
                </tr>
              )}
              {isLoading && (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-sm text-outline">Đang tải dữ liệu bài thi...</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-surface-variant flex items-center justify-between text-sm text-outline">
          <p>Đang hiển thị {filteredExams.length} trong số {overview.items.length} bài thi</p>
        </div>
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
    </div>
  );
}
