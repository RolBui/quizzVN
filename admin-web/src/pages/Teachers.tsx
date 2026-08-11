import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  Download,
  Loader2,
  Pencil,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { MetricSparklineCard } from "../components/MetricSparklineCard";
import { PaginationBar } from "../components/PaginationBar";
import { TeacherDetail } from "../components/TeacherDetail";
import {
  adminApi,
  type AdminMetric,
  type AdminTeacher,
  type AdminTeacherOverview,
} from "../lib/api";
import { useAppNotifications } from "../lib/app-notifications";
import { datedExcelFilename, downloadExcel } from "../lib/exportExcel";
import { formatDate, formatNumber, initials } from "../lib/format";

const PAGE_SIZE = 7;

const fallbackOverview: AdminTeacherOverview = {
  metrics: [],
  items: [],
};

const metricPalettes: Record<string, { stroke: string; fill: string }> = {
  total_teachers: {
    stroke: "#f59e0b",
    fill: "rgba(245, 158, 11, 0.24)",
  },
  active_teachers: {
    stroke: "#10b981",
    fill: "rgba(16, 185, 129, 0.24)",
  },
  total_exams: {
    stroke: "#ec4899",
    fill: "rgba(236, 72, 153, 0.24)",
  },
  total_classes: {
    stroke: "#818cf8",
    fill: "rgba(129, 140, 248, 0.26)",
  },
};

const fallbackPalette = {
  stroke: "#94a3b8",
  fill: "rgba(148, 163, 184, 0.24)",
};

function MetricCard({ metric }: { metric: AdminMetric }) {
  return (
    <MetricSparklineCard
      label={metric.label}
      value={formatNumber(metric.value, metric.suffix)}
      trend={metric.trend}
      isUp={metric.is_up}
      subtext={metric.subtext}
      sparkline={metric.sparkline}
      palette={metricPalettes[metric.key] ?? fallbackPalette}
    />
  );
}

function TeacherAvatar({ teacher }: { teacher: AdminTeacher }) {
  if (teacher.avatar_url) {
    return (
      <img
        src={teacher.avatar_url}
        alt={teacher.full_name}
        className="w-10 h-10 rounded-full object-cover"
      />
    );
  }
  return (
    <div className="w-10 h-10 rounded-full bg-primary-fixed-dim text-on-primary-fixed flex items-center justify-center font-semibold text-sm">
      {initials(teacher.full_name)}
    </div>
  );
}

export function Teachers() {
  const { addNotification } = useAppNotifications();
  const [overview, setOverview] =
    useState<AdminTeacherOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingTeacher, setDeletingTeacher] = useState<AdminTeacher | null>(
    null,
  );
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedTeacher, setSelectedTeacher] = useState<AdminTeacher | null>(
    null,
  );
  const [currentPage, setCurrentPage] = useState(1);

  const loadTeachers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminApi.getTeachersOverview();
      setOverview(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách giáo viên.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTeachers();
  }, [loadTeachers]);
  const closeDeleteModal = () => {
    if (isDeleting) {
      return;
    }
    setDeletingTeacher(null);
    setDeleteError(null);
  };

  const handleDeleteTeacher = async () => {
    if (!deletingTeacher) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);
    setError(null);
    try {
      await adminApi.deleteTeacher(deletingTeacher.id);
      await loadTeachers();
      setDeletingTeacher(null);
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Không xóa được giáo viên.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredTeachers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((teacher) => {
      const matchesStatus =
        status === "all" ||
        (status === "online" ? teacher.is_online : !teacher.is_online);
      const matchesQuery =
        !normalizedQuery ||
        teacher.full_name.toLowerCase().includes(normalizedQuery) ||
        teacher.email.toLowerCase().includes(normalizedQuery) ||
        teacher.code.toLowerCase().includes(normalizedQuery);
      return matchesStatus && matchesQuery;
    });
  }, [overview.items, query, status]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredTeachers.length / PAGE_SIZE),
  );
  const paginatedTeachers = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredTeachers.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, filteredTeachers]);

  const handleExportTeachers = () => {
    downloadExcel({
      filename: datedExcelFilename("giao-vien"),
      sheetName: "Giao vien",
      columns: [
        { header: "ID", value: (teacher) => teacher.code },
        { header: "Họ tên", value: (teacher) => teacher.full_name },
        { header: "Tên đăng nhập", value: (teacher) => teacher.username },
        { header: "Email", value: (teacher) => teacher.email },
        { header: "Số điện thoại", value: (teacher) => teacher.phone || "" },
        {
          header: "Trường",
          value: (teacher) => teacher.school_name || "Chưa cập nhật",
        },
        {
          header: "Ngày sinh",
          value: (teacher) => formatDate(teacher.date_of_birth),
        },
        { header: "Giới tính", value: (teacher) => teacher.gender || "" },
        { header: "Số lớp", value: (teacher) => teacher.class_count },
        { header: "Đề thi", value: (teacher) => teacher.exam_count },
        { header: "Tài liệu", value: (teacher) => teacher.document_count },
        {
          header: "Trạng thái tài khoản",
          value: (teacher) =>
            teacher.status === "active" ? "Hoạt động" : "Bị khóa",
        },
        {
          header: "Trạng thái hoạt động",
          value: (teacher) =>
            teacher.is_online ? "Đang hoạt động" : "Không hoạt động",
        },
        {
          header: "Đăng nhập cuối",
          value: (teacher) => formatDate(teacher.last_login_at),
        },
        {
          header: "Ngày tạo",
          value: (teacher) => formatDate(teacher.created_at),
        },
      ],
      rows: filteredTeachers,
    });
    addNotification({
      type: "data_export",
      title: "Đã xuất danh sách giáo viên",
      body: `${filteredTeachers.length} giáo viên đã được xuất ra file Excel.`,
    });
  };

  useEffect(() => {
    setCurrentPage(1);
  }, [query, status]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  if (selectedTeacher) {
    return (
      <TeacherDetail
        teacher={selectedTeacher}
        onBack={() => setSelectedTeacher(null)}
        onSaved={(teacher) => {
          setSelectedTeacher(teacher);
          setOverview((current) => ({
            ...current,
            items: current.items.map((item) =>
              item.id === teacher.id ? teacher : item,
            ),
          }));
        }}
        onDeleted={() => {
          setSelectedTeacher(null);
          void loadTeachers();
        }}
      />
    );
  }

  return (
    <div className="p-4 flex flex-col gap-4 h-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-lg font-semibold text-on-surface">
            Danh sách Giáo viên
          </h1>
        </div>
        <button
          type="button"
          onClick={handleExportTeachers}
          disabled={isLoading || filteredTeachers.length === 0}
          className="w-full px-4 py-2 bg-surface-container-lowest border border-primary text-primary rounded-lg text-sm font-semibold hover:bg-primary/10 transition-colors flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          <Download className="w-4 h-4" /> Xuất dữ liệu
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {(overview.metrics.length
          ? overview.metrics
          : fallbackOverview.metrics
        ).map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) flex flex-col overflow-hidden">
        <div className="p-4 border-b border-surface-variant bg-surface-container-lowest flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm giáo viên theo tên, mã hoặc email..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none placeholder:text-outline"
            />
          </div>
          <div className="relative w-full sm:w-40">
            <select
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              className="w-full appearance-none bg-surface-container-low border border-surface-variant text-on-surface text-sm py-2 pl-3 pr-8 rounded-lg focus:outline-none focus:border-primary cursor-pointer"
            >
            <option value="all">Tất cả trạng thái</option>
            <option value="online">Hoạt động</option>
            <option value="offline">Không hoạt động</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/50 border-b border-surface-variant">
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Giáo viên
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  ID
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Lớp
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Đề thi
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Tài liệu
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Ngày tạo
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Trạng thái
                </th>
                <th className="py-3 px-4 w-[96px] text-xs font-bold text-on-surface-variant tracking-wider text-center">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50 flex-1">
              {paginatedTeachers.map((teacher) => (
                <tr
                  key={teacher.id}
                  className="hover:bg-surface-container-low/30 transition-colors cursor-pointer"
                  onClick={() => setSelectedTeacher(teacher)}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <TeacherAvatar teacher={teacher} />
                      <div>
                        <p className="font-medium text-sm text-on-surface">
                          {teacher.full_name}
                        </p>
                        <p className="text-xs text-on-surface-variant">
                          {teacher.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">
                    {teacher.code}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">
                    {teacher.class_count}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">
                    {teacher.exam_count}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">
                    {teacher.document_count}
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">
                    {formatDate(teacher.created_at)}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`badge ${teacher.is_online ? "badge-success" : "badge-secondary"}`}
                    >
                      {teacher.is_online ? "Hoạt động" : "Không hoạt động"}
                    </span>
                  </td>
                  <td className="py-3 px-4 w-[96px] text-center">
                    <div className="inline-flex items-center gap-1">
                      <button
                        className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors"
                        title="Sửa giáo viên"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedTeacher(teacher);
                        }}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        className="text-outline hover:text-error p-2 rounded hover:bg-error-container transition-colors"
                        title="Xóa giáo viên"
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeletingTeacher(teacher);
                          setDeleteError(null);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!isLoading && filteredTeachers.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Chưa có giáo viên phù hợp.
                  </td>
                </tr>
              )}
              {isLoading && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Đang tải dữ liệu giáo viên...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar
          page={currentPage}
          pageSize={PAGE_SIZE}
          totalItems={filteredTeachers.length}
          onPageChange={setCurrentPage}
        />
      </div>

      {deletingTeacher && (
        <div className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-md bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-on-surface">
                    Xóa giáo viên
                  </h2>
                  <p className="text-sm text-outline mt-1">
                    Giáo viên sẽ bị xóa khỏi danh sách quản lý.
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
                void handleDeleteTeacher();
              }}
              className="p-5 space-y-4"
            >
              <div className="rounded-lg border border-error-container bg-error-container/40 px-4 py-3">
                <p className="text-sm text-on-surface">
                  Bạn có chắc muốn xóa giáo viên này?
                </p>
                <p className="text-sm font-semibold text-on-surface mt-2">
                  {deletingTeacher.full_name}
                </p>
                <p className="text-xs text-outline mt-1">
                  {deletingTeacher.email}
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
                  Xóa giáo viên
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
