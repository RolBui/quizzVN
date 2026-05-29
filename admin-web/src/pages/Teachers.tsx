import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
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
import { TeacherDetail } from "../components/TeacherDetail";
import {
  adminApi,
  chatApi,
  type AdminMetric,
  type AdminTeacher,
  type AdminTeacherOverview,
} from "../lib/api";
import { formatDate, formatNumber, initials } from "../lib/format";

const PAGE_SIZE = 7;

const fallbackOverview: AdminTeacherOverview = {
  metrics: [],
  items: [],
};

const metricPalettes: Record<string, { stroke: string; fill: string }> = {
  total_teachers: {
    stroke: "#e5a76f",
    fill: "rgba(229, 167, 111, 0.16)",
  },
  active_teachers: {
    stroke: "#8fd5b5",
    fill: "rgba(143, 213, 181, 0.18)",
  },
  total_exams: {
    stroke: "#f3a0c4",
    fill: "rgba(243, 160, 196, 0.18)",
  },
  total_classes: {
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
  const navigate = useNavigate();
  const [overview, setOverview] =
    useState<AdminTeacherOverview>(fallbackOverview);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [openingChatTeacherId, setOpeningChatTeacherId] = useState<
    number | null
  >(null);
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

  const openTeacherChat = async (teacher: AdminTeacher) => {
    if (openingChatTeacherId) {
      return;
    }

    setError(null);
    setOpeningChatTeacherId(teacher.id);
    try {
      const response = await chatApi.createConversation(teacher.id);
      navigate("/chat", {
        state: { conversationId: response.conversation.id },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể mở tin nhắn.");
    } finally {
      setOpeningChatTeacherId(null);
    }
  };

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
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6 h-full">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-semibold text-on-surface">
            Danh sách Giáo viên
          </h1>
        </div>
        <button className="px-4 py-2 bg-surface border border-primary text-primary rounded-lg text-sm font-medium hover:bg-primary/5 transition-colors flex items-center gap-2">
          <Download className="w-4 h-4" /> Xuất dữ liệu
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-500" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {(overview.metrics.length
          ? overview.metrics
          : fallbackOverview.metrics
        ).map((metric) => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) flex flex-col overflow-hidden">
        <div className="p-4 border-b border-outline-variant bg-surface-container-lowest flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="relative w-full max-w-md">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm giáo viên theo tên, mã hoặc email..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
            className="bg-surface-container-low border border-outline-variant text-on-surface text-sm py-2 px-3 rounded-md focus:outline-none focus:border-primary w-full md:w-auto"
          >
            <option value="all">Tất cả trạng thái</option>
            <option value="online">Hoạt động</option>
            <option value="offline">Không hoạt động</option>
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
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
                <th className="py-3 px-4 w-[132px] text-xs font-bold text-on-surface-variant tracking-wider text-center">
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
                      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${teacher.is_online ? "bg-[#10B981]/10 text-[#10B981]" : "bg-surface-variant text-on-surface-variant"}`}
                    >
                      {teacher.is_online ? "Hoạt động" : "Không hoạt động"}
                    </span>
                  </td>
                  <td className="py-3 px-4 w-[132px] text-center">
                    <div className="inline-flex items-center gap-1">
                      <button
                        className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors disabled:opacity-60"
                        title="Nhắn tin"
                        disabled={openingChatTeacherId === teacher.id}
                        onClick={(event) => {
                          event.stopPropagation();
                          void openTeacherChat(teacher);
                        }}
                      >
                        {openingChatTeacherId === teacher.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <MessageSquare className="w-4 h-4" />
                        )}
                      </button>
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
