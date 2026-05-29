import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, CheckCircle2, ClipboardList, Edit, Eye, Filter, Search } from "lucide-react";
import { adminApi, type AdminExam, type AdminExamOverview } from "../lib/api";
import { formatDateTime, formatDecimal, formatNumber, scopeLabel } from "../lib/format";

const fallbackOverview: AdminExamOverview = {
  metrics: [],
  items: [],
};

function examStatus(exam: AdminExam) {
  if (!exam.is_published) {
    return { label: "Bản nháp", className: "text-outline bg-surface-variant", icon: Edit };
  }
  if (exam.is_active) {
    return { label: "Đang mở", className: "text-primary bg-primary/10", icon: CheckCircle2 };
  }
  return { label: "Đã đóng", className: "text-[#10B981] bg-[#10B981]/10", icon: CheckCircle2 };
}

export function Exams() {
  const [overview, setOverview] = useState<AdminExamOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  const averageMetric = overview.metrics.find((metric) => metric.key === "average_score");
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
            <p className="text-sm font-medium text-outline">{averageMetric?.label || "Điểm trung bình"}</p>
            <div className="w-8 h-8 rounded bg-primary-container text-on-primary-container flex items-center justify-center">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-on-surface">{formatDecimal(averageMetric?.value, "%")}</p>
          <p className="text-xs text-outline">{averageMetric?.subtext || "trên bài đã nộp"}</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
            <p className="text-sm font-medium text-outline">{submittedMetric?.label || "Lượt hoàn thành"}</p>
            <div className="w-8 h-8 rounded bg-green-100 text-green-700 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-on-surface">{formatNumber(submittedMetric?.value)}</p>
          <p className="text-xs text-outline">{submittedMetric?.subtext || "bài làm đã nộp"}</p>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
            <p className="text-sm font-medium text-outline">{activeMetric?.label || "Bài thi đang mở"}</p>
            <div className="w-8 h-8 rounded bg-secondary-container text-on-secondary-container flex items-center justify-center">
              <ClipboardList className="w-4 h-4" />
            </div>
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
          <table className="w-full text-left border-collapse min-w-225">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-lowest text-outline">
                <th className="py-4 px-6 text-xs font-semibold">Tên Bài thi</th>
                <th className="py-4 px-6 text-xs font-semibold">Scope</th>
                <th className="py-4 px-6 text-xs font-semibold">Giáo viên</th>
                <th className="py-4 px-6 text-xs font-semibold">Câu hỏi</th>
                <th className="py-4 px-6 text-xs font-semibold">Lượt làm</th>
                <th className="py-4 px-6 text-xs font-semibold">Điểm TB</th>
                <th className="py-4 px-6 text-xs font-semibold">Ngày tạo</th>
                <th className="py-4 px-6 text-xs font-semibold">Trạng thái</th>
                <th className="py-4 px-6 text-xs font-semibold text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {filteredExams.map((exam) => {
                const status = examStatus(exam);
                const StatusIcon = status.icon;
                return (
                  <tr key={exam.id} className="hover:bg-surface-container-low/50 transition-colors bg-surface-container-lowest">
                    <td className="py-4 px-6">
                      <p className="text-sm font-medium text-primary">{exam.title}</p>
                      <p className="text-xs text-outline">{exam.classroom_name || "Không gắn lớp"}</p>
                    </td>
                    <td className="py-4 px-6 text-sm text-outline font-medium">{scopeLabel(exam.scope)}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.teacher_name || "Chưa xác định"}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.question_count}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.attempt_count}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{exam.average_score === null ? "Chưa có" : formatDecimal(exam.average_score, "%")}</td>
                    <td className="py-4 px-6 text-sm text-on-surface">{formatDateTime(exam.created_at)}</td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${status.className}`}>
                        <StatusIcon className="w-3 h-3" />
                        {status.label}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      <button className="text-outline hover:text-primary transition-colors"><Eye className="w-4 h-4" /></button>
                    </td>
                  </tr>
                );
              })}
              {!isLoading && filteredExams.length === 0 && (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-sm text-outline">Chưa có bài thi phù hợp.</td>
                </tr>
              )}
              {isLoading && (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-sm text-outline">Đang tải dữ liệu bài thi...</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 border-t border-surface-variant flex items-center justify-between text-sm text-outline">
          <p>Đang hiển thị {filteredExams.length} trong số {overview.items.length} bài thi</p>
        </div>
      </div>
    </div>
  );
}
