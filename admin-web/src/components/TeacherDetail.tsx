import {
  FormEvent,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  Edit,
  FileText,
  Loader2,
  Mail,
  MapPin,
  MoreVertical,
  RefreshCw,
  Trash2,
  Users,
  X,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  adminApi,
  chatApi,
  type AdminMetric,
  type AdminTeacher,
  type AdminTeacherDetail as AdminTeacherDetailData,
} from "../lib/api";
import {
  formatDate,
  formatDateTime,
  formatNumber,
  initials,
} from "../lib/format";

interface TeacherDetailProps {
  teacher: AdminTeacher;
  onBack: () => void;
  onSaved?: (teacher: AdminTeacher) => void;
  onDeleted?: () => void;
}

interface ProfileFormState {
  full_name: string;
  email: string;
  phone: string;
  school_name: string;
  date_of_birth: string;
  gender: string;
  status: "active" | "disabled";
}

const metricIcons: Record<string, typeof BookOpen> = {
  total_classes: BookOpen,
  total_students: Users,
  total_exams: FileText,
  total_documents: FileText,
};

function genderLabel(gender: string | null) {
  if (gender === "male") return "Nam";
  if (gender === "female") return "Nữ";
  if (gender === "other") return "Khác";
  return "Chưa cập nhật";
}

function activityBadge(isOnline: boolean) {
  return isOnline
    ? "bg-[#10B981]/10 text-[#10B981]"
    : "bg-surface-variant text-on-surface-variant";
}

function statusLabel(status: string) {
  return status === "disabled" ? "Vô hiệu hóa" : "Hoạt động";
}

function buildForm(teacher: AdminTeacher): ProfileFormState {
  return {
    full_name: teacher.full_name,
    email: teacher.email,
    phone: teacher.phone ?? "",
    school_name: teacher.school_name ?? "",
    date_of_birth: teacher.date_of_birth ?? "",
    gender: teacher.gender ?? "other",
    status: teacher.status === "disabled" ? "disabled" : "active",
  };
}

function MetricCard({ metric }: { metric: AdminMetric }) {
  const Icon = metricIcons[metric.key] ?? FileText;
  return (
    <div className="bg-surface-container-lowest p-5 rounded-xl shadow-sm border border-outline-variant/30 flex flex-col justify-between min-h-[132px]">
      <div className="flex justify-between items-start mb-3">
        <p className="text-sm font-medium text-on-surface-variant">
          {metric.label}
        </p>
        <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div>
        <p className="text-3xl font-bold text-on-surface">
          {formatNumber(metric.value, metric.suffix)}
        </p>
        <p className="text-xs text-on-surface-variant font-medium mt-2">
          {metric.subtext}
        </p>
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="py-12 text-center text-sm text-on-surface-variant">
      {label}
    </div>
  );
}

export function TeacherDetail({
  teacher,
  onBack,
  onSaved,
  onDeleted,
}: TeacherDetailProps) {
  const navigate = useNavigate();
  const [detail, setDetail] = useState<AdminTeacherDetailData | null>(null);
  const [activeTab, setActiveTab] = useState("classes");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [form, setForm] = useState<ProfileFormState>(() => buildForm(teacher));
  const [password, setPassword] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isOpeningChat, setIsOpeningChat] = useState(false);

  const currentTeacher = detail?.teacher ?? teacher;
  const metrics = useMemo(
    () =>
      detail?.metrics ?? [
        {
          key: "total_classes",
          label: "Tổng số lớp học",
          value: currentTeacher.class_count,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "lớp do giáo viên tạo",
          sparkline: [],
        },
        {
          key: "total_students",
          label: "Tổng số học sinh",
          value: 0,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "trong tất cả lớp",
          sparkline: [],
        },
        {
          key: "total_exams",
          label: "Đề thi đã tạo",
          value: currentTeacher.exam_count,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "từ tài khoản giáo viên",
          sparkline: [],
        },
        {
          key: "total_documents",
          label: "Tài liệu",
          value: currentTeacher.document_count,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "tài liệu đã tạo",
          sparkline: [],
        },
      ],
    [currentTeacher, detail],
  );

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminApi
      .getTeacherDetail(teacher.id)
      .then((response) => {
        if (!isMounted) return;
        setDetail(response);
        setForm(buildForm(response.teacher));
        onSaved?.(response.teacher);
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Không tải được chi tiết giáo viên.",
          );
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [teacher.id]);

  const handleOpenChat = async () => {
    if (isOpeningChat) return;
    setActionError(null);
    setIsOpeningChat(true);
    try {
      const response = await chatApi.createConversation(currentTeacher.id);
      navigate("/chat", {
        state: { conversationId: response.conversation.id },
      });
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Không mở được tin nhắn.",
      );
    } finally {
      setIsOpeningChat(false);
    }
  };

  const handleSaveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActionError(null);
    setIsSaving(true);
    try {
      const response = await adminApi.updateTeacherProfile(currentTeacher.id, {
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        school_name: form.school_name,
        date_of_birth: form.date_of_birth || undefined,
        gender: form.gender,
        status: form.status,
      });
      setDetail(response);
      onSaved?.(response.teacher);
      setIsEditOpen(false);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Không lưu được thông tin.",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleResetPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActionError(null);
    setIsResetting(true);
    try {
      await adminApi.resetTeacherPassword(currentTeacher.id, password);
      setPassword("");
      setIsResetOpen(false);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Không đặt lại được mật khẩu.",
      );
    } finally {
      setIsResetting(false);
    }
  };

  const handleDelete = async () => {
    setActionError(null);
    setIsDeleting(true);
    try {
      await adminApi.deleteTeacher(currentTeacher.id);
      onDeleted?.();
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Không xóa được tài khoản.",
      );
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="p-4 md:p-6 flex flex-col gap-6 h-full bg-surface">
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-surface-variant/50 rounded-lg text-outline transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold text-on-surface">
            Chi tiết Giáo viên
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => {
              setForm(buildForm(currentTeacher));
              setActionError(null);
              setIsEditOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-variant/30 transition-colors"
          >
            <Edit className="w-4 h-4" /> Sửa thông tin
          </button>
          <button
            onClick={() => {
              setActionError(null);
              setPassword("");
              setIsResetOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg text-sm font-medium hover:bg-surface-variant/30 transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> Đặt lại mật khẩu
          </button>
          <button
            onClick={() => void handleOpenChat()}
            disabled={isOpeningChat}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-70"
          >
            {isOpeningChat ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Mail className="w-4 h-4" />
            )}
            Gửi tin nhắn
          </button>
          <button
            onClick={() => {
              setActionError(null);
              setIsDeleteOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 border border-red-100 rounded-lg text-sm font-medium hover:bg-red-100 transition-colors"
          >
            <Trash2 className="w-4 h-4" /> Xóa tài khoản
          </button>
        </div>
      </div>

      {(error || actionError) && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-on-surface">
          {error || actionError}
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6 items-start">
        <div className="w-full lg:w-80 shrink-0 bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 p-6 flex flex-col">
          <div className="flex flex-col items-center mb-6">
            <div className="relative mb-4">
              {currentTeacher.avatar_url ? (
                <img
                  src={currentTeacher.avatar_url}
                  alt={currentTeacher.full_name}
                  className="w-24 h-24 rounded-full object-cover shadow-sm border-2 border-surface"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-primary-fixed-dim text-on-primary-fixed flex items-center justify-center font-bold text-3xl shadow-sm border-2 border-surface">
                  {initials(currentTeacher.full_name)}
                </div>
              )}
              <div
                className={`absolute bottom-1 right-1 w-4 h-4 rounded-full border-2 border-surface ${
                  currentTeacher.is_online ? "bg-emerald-500" : "bg-outline"
                }`}
              />
            </div>
            <h2 className="text-xl font-bold text-on-surface mb-2">
              {currentTeacher.full_name}
            </h2>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-surface-variant/50 text-on-surface-variant rounded text-xs font-semibold">
                {currentTeacher.code}
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${activityBadge(currentTeacher.is_online)}`}
              >
                {currentTeacher.is_online ? "Hoạt động" : "Không hoạt động"}
              </span>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <h3 className="text-xs font-bold text-outline uppercase tracking-wider mb-4">
                Thông tin liên hệ
              </h3>
              <div className="space-y-4">
                <InfoRow
                  icon={Mail}
                  label="Địa chỉ Email"
                  value={currentTeacher.email}
                />
                <InfoRow
                  icon={Calendar}
                  label="Ngày sinh"
                  value={formatDate(currentTeacher.date_of_birth)}
                />
                <InfoRow
                  icon={Users}
                  label="Giới tính"
                  value={genderLabel(currentTeacher.gender)}
                />
                <InfoRow
                  icon={MapPin}
                  label="Trường"
                  value={currentTeacher.school_name || "Chưa cập nhật"}
                />
              </div>
            </div>

            <div>
              <h3 className="text-xs font-bold text-outline uppercase tracking-wider mb-4">
                Thông tin hệ thống
              </h3>
              <div className="flex flex-col gap-4">
                <SystemRow
                  label="Trạng thái tài khoản"
                  value={statusLabel(currentTeacher.status)}
                />
                <SystemRow
                  label="Ngày gia nhập"
                  value={formatDate(currentTeacher.created_at)}
                />
                <SystemRow
                  label="Đăng nhập cuối"
                  value={formatDateTime(currentTeacher.last_login_at)}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            {metrics.map((metric) => (
              <MetricCard key={metric.key} metric={metric} />
            ))}
          </div>

          <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/30 flex-1 flex flex-col overflow-hidden">
            <div className="flex border-b border-outline-variant/30 overflow-x-auto">
              {[
                ["classes", "Lớp học"],
                ["exams", "Đề thi"],
                ["documents", "Tài liệu"],
                ["activity", "Lịch sử hoạt động"],
              ].map(([key, label]) => (
                <button
                  key={key}
                  className={`px-6 py-4 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                    activeTab === key
                      ? "border-indigo-600 text-indigo-600"
                      : "border-transparent text-on-surface-variant hover:text-on-surface"
                  }`}
                  onClick={() => setActiveTab(key)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-x-auto">
              {isLoading ? (
                <EmptyState label="Đang tải dữ liệu chi tiết..." />
              ) : activeTab === "classes" ? (
                <ClassesTable detail={detail} />
              ) : activeTab === "exams" ? (
                <ExamsTable detail={detail} />
              ) : activeTab === "documents" ? (
                <DocumentsTable detail={detail} />
              ) : (
                <ActivityPanel teacher={currentTeacher} />
              )}
            </div>
          </div>
        </div>
      </div>

      {isEditOpen && (
        <Modal
          title="Sửa thông tin giáo viên"
          onClose={() => !isSaving && setIsEditOpen(false)}
        >
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <ProfileFields form={form} setForm={setForm} />
            <ModalActions
              submitLabel="Lưu thông tin"
              isSubmitting={isSaving}
              onCancel={() => setIsEditOpen(false)}
            />
          </form>
        </Modal>
      )}

      {isResetOpen && (
        <Modal
          title="Đặt lại mật khẩu"
          onClose={() => !isResetting && setIsResetOpen(false)}
        >
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <label className="text-sm font-medium text-on-surface">
                Mật khẩu mới
              </label>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                minLength={6}
                required
                className="mt-2 w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-sm outline-none focus:border-primary"
              />
            </div>
            <ModalActions
              submitLabel="Đặt lại"
              isSubmitting={isResetting}
              onCancel={() => setIsResetOpen(false)}
            />
          </form>
        </Modal>
      )}

      {isDeleteOpen && (
        <Modal
          title="Xóa tài khoản giáo viên"
          onClose={() => !isDeleting && setIsDeleteOpen(false)}
        >
          <div className="space-y-4">
            <p className="text-sm text-on-surface-variant">
              Xóa tài khoản {currentTeacher.email}? Tài khoản sẽ bị xóa khỏi
              danh sách quản lý.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsDeleteOpen(false)}
                className="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium"
              >
                Hủy
              </button>
              <button
                onClick={() => void handleDelete()}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium disabled:opacity-70"
              >
                {isDeleting ? "Đang xóa..." : "Xóa tài khoản"}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

function InfoRow({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Mail;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon className="w-4 h-4 text-outline mt-0.5" />
      <div>
        <p className="text-xs text-on-surface-variant mb-0.5">{label}</p>
        <p className="text-sm font-medium text-on-surface break-all">{value}</p>
      </div>
    </div>
  );
}

function SystemRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center gap-4">
      <p className="text-xs text-on-surface-variant">{label}</p>
      <p className="text-sm font-medium text-on-surface text-right">{value}</p>
    </div>
  );
}

function ClassesTable({ detail }: { detail: AdminTeacherDetailData | null }) {
  if (!detail?.classes.length) return <EmptyState label="Chưa có lớp học." />;
  return (
    <table className="w-full text-left border-collapse min-w-[760px]">
      <thead>
        <tr className="border-b border-outline-variant/30">
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Tên lớp
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Mã lớp
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Học sinh
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Đề thi
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Tài liệu
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase text-right">
            Thao tác
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-outline-variant/20">
        {detail.classes.map((classroom) => (
          <tr
            key={classroom.id}
            className="hover:bg-surface-variant/10 transition-colors"
          >
            <td className="py-4 px-6">
              <p className="font-semibold text-sm text-on-surface">
                {classroom.name}
              </p>
              <p className="text-xs text-on-surface-variant mt-0.5">
                {classroom.description || "Không có mô tả"}
              </p>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {classroom.join_code}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {classroom.student_count}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {classroom.exam_count}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {classroom.document_count}
            </td>
            <td className="py-4 px-6 text-right">
              <MoreVertical className="w-5 h-5 ml-auto text-outline" />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ExamsTable({ detail }: { detail: AdminTeacherDetailData | null }) {
  if (!detail?.exams.length) return <EmptyState label="Chưa có đề thi." />;
  return (
    <table className="w-full text-left border-collapse min-w-[820px]">
      <thead>
        <tr className="border-b border-outline-variant/30">
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Đề thi
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Lớp
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Câu hỏi
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Bài làm
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Trạng thái
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Ngày tạo
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-outline-variant/20">
        {detail.exams.map((exam) => (
          <tr
            key={exam.id}
            className="hover:bg-surface-variant/10 transition-colors"
          >
            <td className="py-4 px-6">
              <p className="font-semibold text-sm text-on-surface">
                {exam.title}
              </p>
              <p className="text-xs text-on-surface-variant mt-0.5">
                {exam.duration_minutes} phút
              </p>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {exam.classroom_name || "Hệ thống"}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {exam.question_count}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {exam.attempt_count}
            </td>
            <td className="py-4 px-6">
              <span
                className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${exam.is_published && exam.is_active ? "bg-[#10B981]/10 text-[#10B981]" : "bg-surface-variant text-on-surface-variant"}`}
              >
                {exam.is_published && exam.is_active ? "Đang mở" : "Đã ẩn"}
              </span>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {formatDate(exam.created_at)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DocumentsTable({ detail }: { detail: AdminTeacherDetailData | null }) {
  if (!detail?.documents.length)
    return <EmptyState label="Chưa có tài liệu." />;
  return (
    <table className="w-full text-left border-collapse min-w-[760px]">
      <thead>
        <tr className="border-b border-outline-variant/30">
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Tài liệu
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Lớp
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Dung lượng chữ
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Trạng thái
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Ngày tạo
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-outline-variant/20">
        {detail.documents.map((document) => (
          <tr
            key={document.id}
            className="hover:bg-surface-variant/10 transition-colors"
          >
            <td className="py-4 px-6">
              <p className="font-semibold text-sm text-on-surface">
                {document.title}
              </p>
              <p className="text-xs text-on-surface-variant mt-0.5 line-clamp-1">
                {document.summary ||
                  document.content_preview ||
                  "Không có mô tả"}
              </p>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {document.classroom_name || "Hệ thống"}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {document.content_length}
            </td>
            <td className="py-4 px-6">
              <span
                className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${document.is_published ? "bg-[#10B981]/10 text-[#10B981]" : "bg-surface-variant text-on-surface-variant"}`}
              >
                {document.is_published ? "Đã xuất bản" : "Đã ẩn"}
              </span>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {formatDate(document.created_at)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ActivityPanel({ teacher }: { teacher: AdminTeacher }) {
  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
      <SystemTile
        label="Trạng thái tài khoản"
        value={statusLabel(teacher.status)}
      />
      <SystemTile
        label="Ngày gia nhập"
        value={formatDateTime(teacher.created_at)}
      />
      <SystemTile
        label="Đăng nhập cuối"
        value={formatDateTime(teacher.last_login_at)}
      />
    </div>
  );
}

function SystemTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-outline-variant/40 bg-surface p-4">
      <p className="text-xs text-on-surface-variant">{label}</p>
      <p className="text-sm font-semibold text-on-surface mt-2">{value}</p>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-scrim/40 p-4">
      <div className="w-full max-w-lg rounded-xl bg-surface-container-lowest shadow-xl border border-outline-variant">
        <div className="flex items-center justify-between px-5 py-4 border-b border-outline-variant">
          <h2 className="text-lg font-semibold text-on-surface">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-variant/40"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function ProfileFields({
  form,
  setForm,
}: {
  form: ProfileFormState;
  setForm: Dispatch<SetStateAction<ProfileFormState>>;
}) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <TextField
          label="Họ tên"
          value={form.full_name}
          onChange={(value) =>
            setForm((current) => ({ ...current, full_name: value }))
          }
          required
        />
        <TextField
          label="Email"
          type="email"
          value={form.email}
          onChange={(value) =>
            setForm((current) => ({ ...current, email: value }))
          }
          required
        />
        <TextField
          label="Số điện thoại"
          value={form.phone}
          onChange={(value) =>
            setForm((current) => ({ ...current, phone: value }))
          }
        />
        <TextField
          label="Trường"
          value={form.school_name}
          onChange={(value) =>
            setForm((current) => ({ ...current, school_name: value }))
          }
        />
        <TextField
          label="Ngày sinh"
          type="date"
          value={form.date_of_birth}
          onChange={(value) =>
            setForm((current) => ({ ...current, date_of_birth: value }))
          }
        />
        <div>
          <label className="text-sm font-medium text-on-surface">
            Giới tính
          </label>
          <select
            value={form.gender}
            onChange={(event) =>
              setForm((current) => ({ ...current, gender: event.target.value }))
            }
            className="mt-2 w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-sm outline-none focus:border-primary"
          >
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
            <option value="other">Khác</option>
          </select>
        </div>
      </div>
      <div>
        <label className="text-sm font-medium text-on-surface">
          Trạng thái tài khoản
        </label>
        <select
          value={form.status}
          onChange={(event) =>
            setForm((current) => ({
              ...current,
              status: event.target.value as "active" | "disabled",
            }))
          }
          className="mt-2 w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-sm outline-none focus:border-primary"
        >
          <option value="active">Hoạt động</option>
          <option value="disabled">Vô hiệu hóa</option>
        </select>
      </div>
    </>
  );
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label className="text-sm font-medium text-on-surface">{label}</label>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-sm outline-none focus:border-primary"
      />
    </div>
  );
}

function ModalActions({
  submitLabel,
  isSubmitting,
  onCancel,
}: {
  submitLabel: string;
  isSubmitting: boolean;
  onCancel: () => void;
}) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <button
        type="button"
        onClick={onCancel}
        disabled={isSubmitting}
        className="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium disabled:opacity-70"
      >
        Hủy
      </button>
      <button
        type="submit"
        disabled={isSubmitting}
        className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-medium disabled:opacity-70"
      >
        {isSubmitting ? "Đang xử lý..." : submitLabel}
      </button>
    </div>
  );
}
