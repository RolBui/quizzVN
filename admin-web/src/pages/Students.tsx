import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  Download,
  Loader2,
  MessageSquare,
  Pencil,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { MetricSparklineCard } from "../components/MetricSparklineCard";
import { PaginationBar } from "../components/PaginationBar";
import { StudentDetail } from "../components/StudentDetail";
import {
  adminApi,
  chatApi,
  type AdminMetric,
  type AdminStudent,
  type AdminStudentOverview,
} from "../lib/api";
import { useAppNotifications } from "../lib/app-notifications";
import { datedExcelFilename, downloadExcel } from "../lib/exportExcel";
import { formatDate, formatNumber, initials } from "../lib/format";

const PAGE_SIZE = 7;

const fallbackOverview: AdminStudentOverview = {
  metrics: [],
  items: [],
};

const metricPalettes: Record<string, { stroke: string; fill: string }> = {
  total_students: {
    stroke: "#e5a76f",
    fill: "rgba(229, 167, 111, 0.16)",
  },
  new_students: {
    stroke: "#8fd5b5",
    fill: "rgba(143, 213, 181, 0.18)",
  },
  active_students: {
    stroke: "#f3a0c4",
    fill: "rgba(243, 160, 196, 0.18)",
  },
  disabled_students: {
    stroke: "#a8a8f0",
    fill: "rgba(168, 168, 240, 0.18)",
  },
};

const fallbackPalette = {
  stroke: "#94a3b8",
  fill: "rgba(148, 163, 184, 0.16)",
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

function StudentAvatar({ student }: { student: AdminStudent }) {
  if (student.avatar_url) {
    return (
      <img
        src={student.avatar_url}
        alt={student.full_name}
        className="w-10 h-10 rounded-full object-cover border border-outline-variant/30"
      />
    );
  }
  return (
    <div className="w-10 h-10 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-sm border border-outline-variant/30">
      {initials(student.full_name)}
    </div>
  );
}

export function Students() {
  const navigate = useNavigate();
  const { addNotification } = useAppNotifications();
  const [overview, setOverview] =
    useState<AdminStudentOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openingChatStudentId, setOpeningChatStudentId] = useState<
    number | null
  >(null);
  const [deletingStudent, setDeletingStudent] = useState<AdminStudent | null>(
    null,
  );
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState<AdminStudent | null>(
    null,
  );
  const [currentPage, setCurrentPage] = useState(1);

  const loadStudents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminApi.getStudentsOverview();
      setOverview(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Không thể tải danh sách học sinh.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStudents();
  }, [loadStudents]);

  const openStudentChat = async (student: AdminStudent) => {
    if (openingChatStudentId) {
      return;
    }

    setError(null);
    setOpeningChatStudentId(student.id);
    try {
      const response = await chatApi.createConversation(student.id);
      navigate("/chat", {
        state: { conversationId: response.conversation.id },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể mở tin nhắn.");
    } finally {
      setOpeningChatStudentId(null);
    }
  };

  const closeDeleteModal = () => {
    if (isDeleting) {
      return;
    }
    setDeletingStudent(null);
    setDeleteError(null);
  };

  const handleDeleteStudent = async () => {
    if (!deletingStudent) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);
    setError(null);
    try {
      await adminApi.deleteStudent(deletingStudent.id);
      await loadStudents();
      setDeletingStudent(null);
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Không xóa được học sinh.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredStudents = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return overview.items.filter((student) => {
      const matchesStatus =
        status === "all" ||
        (status === "online" ? student.is_online : !student.is_online);
      const matchesQuery =
        !normalizedQuery ||
        student.full_name.toLowerCase().includes(normalizedQuery) ||
        student.email.toLowerCase().includes(normalizedQuery) ||
        student.code.toLowerCase().includes(normalizedQuery);
      return matchesStatus && matchesQuery;
    });
  }, [overview.items, query, status]);

  const totalPages = Math.max(
    1,
    Math.ceil(filteredStudents.length / PAGE_SIZE),
  );
  const paginatedStudents = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredStudents.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, filteredStudents]);

  const handleExportStudents = () => {
    downloadExcel({
      filename: datedExcelFilename("hoc-sinh"),
      sheetName: "Hoc sinh",
      columns: [
        { header: "Mã số", value: (student) => student.code },
        { header: "Họ tên", value: (student) => student.full_name },
        { header: "Tên đăng nhập", value: (student) => student.username },
        { header: "Email", value: (student) => student.email },
        { header: "Số điện thoại", value: (student) => student.phone || "" },
        {
          header: "Trường",
          value: (student) => student.school_name || "Chưa cập nhật",
        },
        {
          header: "Ngày sinh",
          value: (student) => formatDate(student.date_of_birth),
        },
        { header: "Giới tính", value: (student) => student.gender || "" },
        { header: "Số lớp", value: (student) => student.class_count },
        { header: "Bài làm", value: (student) => student.attempt_count },
        {
          header: "Điểm trung bình",
          value: (student) => student.average_score ?? "",
        },
        {
          header: "Trạng thái tài khoản",
          value: (student) =>
            student.status === "active" ? "Hoạt động" : "Bị khóa",
        },
        {
          header: "Trạng thái hoạt động",
          value: (student) =>
            student.is_online ? "Đang hoạt động" : "Không hoạt động",
        },
        {
          header: "Đăng nhập cuối",
          value: (student) => formatDate(student.last_login_at),
        },
        {
          header: "Ngày tạo",
          value: (student) => formatDate(student.created_at),
        },
      ],
      rows: filteredStudents,
    });
    addNotification({
      type: "data_export",
      title: "Đã xuất danh sách học sinh",
      body: `${filteredStudents.length} học sinh đã được xuất ra file Excel.`,
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

  if (selectedStudent) {
    return (
      <StudentDetail
        student={selectedStudent}
        onBack={() => setSelectedStudent(null)}
        onSaved={(student) => {
          setSelectedStudent(student);
          setOverview((current) => ({
            ...current,
            items: current.items.map((item) =>
              item.id === student.id ? student : item,
            ),
          }));
        }}
        onDeleted={() => {
          setSelectedStudent(null);
          void loadStudents();
        }}
      />
    );
  }

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-lg font-semibold text-on-surface">
            Danh sách Học viên
          </h1>
        </div>
        <button
          type="button"
          onClick={handleExportStudents}
          disabled={isLoading || filteredStudents.length === 0}
          className="w-full px-4 py-2 border border-primary text-primary rounded-lg text-sm font-medium hover:bg-primary/5 transition-colors flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {overview.metrics.map((metric) => (
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
              placeholder="Tìm học sinh theo tên, mã hoặc email..."
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
                  Học sinh
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Mã số
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Trường
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Lớp
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Bài làm
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Ngày tạo
                </th>
                <th className="py-3 px-4 text-xs font-bold text-on-surface-variant tracking-wider">
                  Trạng thái
                </th>
                <th className="py-3 px-4 w-[132px] text-xs font-bold text-on-surface-variant tracking-wider text-center">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50 flex-1">
              {paginatedStudents.map((student) => (
                <tr
                  key={student.id}
                  className="hover:bg-surface-container-low/30 transition-colors cursor-pointer"
                  onClick={() => setSelectedStudent(student)}
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <StudentAvatar student={student} />
                      <div>
                        <p className="font-medium text-sm text-on-surface">
                          {student.full_name}
                        </p>
                        <p className="text-xs text-on-surface-variant">
                          {student.email}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">
                    {student.code}
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">
                    {student.school_name || "Chưa cập nhật"}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">
                    {student.class_count}
                  </td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">
                    {student.attempt_count}
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">
                    {formatDate(student.created_at)}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`badge ${student.is_online ? "badge-success" : "badge-secondary"}`}
                    >
                      {student.is_online ? "Hoạt động" : "Không hoạt động"}
                    </span>
                  </td>
                  <td className="py-3 px-4 w-[132px] text-center">
                    <div className="inline-flex items-center gap-1">
                      <button
                        className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors disabled:opacity-60"
                        title="Nhắn tin"
                        disabled={openingChatStudentId === student.id}
                        onClick={(event) => {
                          event.stopPropagation();
                          void openStudentChat(student);
                        }}
                      >
                        {openingChatStudentId === student.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <MessageSquare className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors"
                        title="Sửa học sinh"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedStudent(student);
                        }}
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        className="text-outline hover:text-error p-2 rounded hover:bg-error-container transition-colors"
                        title="Xóa học sinh"
                        onClick={(event) => {
                          event.stopPropagation();
                          setDeletingStudent(student);
                          setDeleteError(null);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!isLoading && filteredStudents.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Chưa có học sinh phù hợp.
                  </td>
                </tr>
              )}
              {isLoading && (
                <tr>
                  <td
                    colSpan={8}
                    className="py-10 text-center text-sm text-outline"
                  >
                    Đang tải dữ liệu học sinh...
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar
          page={currentPage}
          pageSize={PAGE_SIZE}
          totalItems={filteredStudents.length}
          onPageChange={setCurrentPage}
        />
      </div>

      {deletingStudent && (
        <div className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-md bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-on-surface">
                    Xóa học sinh
                  </h2>
                  <p className="text-sm text-outline mt-1">
                    Học sinh sẽ bị xóa khỏi danh sách quản lý.
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
                void handleDeleteStudent();
              }}
              className="p-5 space-y-4"
            >
              <div className="rounded-lg border border-error-container bg-error-container/40 px-4 py-3">
                <p className="text-sm text-on-surface">
                  Bạn có chắc muốn xóa học sinh này?
                </p>
                <p className="text-sm font-semibold text-on-surface mt-2">
                  {deletingStudent.full_name}
                </p>
                <p className="text-xs text-outline mt-1">
                  {deletingStudent.email}
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
                  Xóa học sinh
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
