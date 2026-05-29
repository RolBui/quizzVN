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
  type AdminStudent,
  type AdminStudentDetail as AdminStudentDetailData,
} from "../lib/api";
import {
  formatDate,
  formatDateTime,
  formatDecimal,
  formatNumber,
  initials,
} from "../lib/format";

interface StudentDetailProps {
  student: AdminStudent;
  onBack: () => void;
  onSaved?: (student: AdminStudent) => void;
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
  submitted_attempts: FileText,
  average_score: Users,
  available_documents: FileText,
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

function buildForm(student: AdminStudent): ProfileFormState {
  return {
    full_name: student.full_name,
    email: student.email,
    phone: student.phone ?? "",
    school_name: student.school_name ?? "",
    date_of_birth: student.date_of_birth ?? "",
    gender: student.gender ?? "other",
    status: student.status === "disabled" ? "disabled" : "active",
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
          {metric.key === "average_score"
            ? formatDecimal(metric.value, metric.suffix)
            : formatNumber(metric.value, metric.suffix)}
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

export function StudentDetail({
  student,
  onBack,
  onSaved,
  onDeleted,
}: StudentDetailProps) {
  const navigate = useNavigate();
  const [detail, setDetail] = useState<AdminStudentDetailData | null>(null);
  const [activeTab, setActiveTab] = useState("classes");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isResetOpen, setIsResetOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [form, setForm] = useState<ProfileFormState>(() => buildForm(student));
  const [password, setPassword] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isOpeningChat, setIsOpeningChat] = useState(false);

  const currentStudent = detail?.student ?? student;
  const metrics = useMemo(
    () =>
      detail?.metrics ?? [
        {
          key: "total_classes",
          label: "Tổng lớp học",
          value: currentStudent.class_count,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "lớp đang tham gia",
          sparkline: [],
        },
        {
          key: "submitted_attempts",
          label: "Bài làm",
          value: currentStudent.attempt_count,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "lượt làm bài",
          sparkline: [],
        },
        {
          key: "average_score",
          label: "Điểm trung bình",
          value: currentStudent.average_score ?? 0,
          suffix: "%",
          trend: "0%",
          is_up: true,
          subtext: "trên bài đã nộp",
          sparkline: [],
        },
        {
          key: "available_documents",
          label: "Tài liệu",
          value: 0,
          suffix: "",
          trend: "0%",
          is_up: true,
          subtext: "có thể xem",
          sparkline: [],
        },
      ],
    [currentStudent, detail],
  );

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    adminApi
      .getStudentDetail(student.id)
      .then((response) => {
        if (!isMounted) return;
        setDetail(response);
        setForm(buildForm(response.student));
        onSaved?.(response.student);
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Không tải được chi tiết học sinh.",
          );
        }
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [student.id]);

  const handleOpenChat = async () => {
    if (isOpeningChat) return;
    setActionError(null);
    setIsOpeningChat(true);
    try {
      const response = await chatApi.createConversation(currentStudent.id);
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
      const response = await adminApi.updateStudentProfile(currentStudent.id, {
        full_name: form.full_name,
        email: form.email,
        phone: form.phone,
        school_name: form.school_name,
        date_of_birth: form.date_of_birth || undefined,
        gender: form.gender,
        status: form.status,
      });
      setDetail(response);
      onSaved?.(response.student);
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
      await adminApi.resetStudentPassword(currentStudent.id, password);
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
      await adminApi.deleteStudent(currentStudent.id);
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
            Chi tiết Học sinh
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => {
              setForm(buildForm(currentStudent));
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
              {currentStudent.avatar_url ? (
                <img
                  src={currentStudent.avatar_url}
                  alt={currentStudent.full_name}
                  className="w-24 h-24 rounded-full object-cover shadow-sm border-2 border-surface"
                />
              ) : (
                <div className="w-24 h-24 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-3xl shadow-sm border-2 border-surface">
                  {initials(currentStudent.full_name)}
                </div>
              )}
              <div
                className={`absolute bottom-1 right-1 w-4 h-4 rounded-full border-2 border-surface ${
                  currentStudent.is_online ? "bg-emerald-500" : "bg-outline"
                }`}
              />
            </div>
            <h2 className="text-xl font-bold text-on-surface mb-2">
              {currentStudent.full_name}
            </h2>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-1 bg-surface-variant/50 text-on-surface-variant rounded text-xs font-semibold">
                {currentStudent.code}
              </span>
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${activityBadge(currentStudent.is_online)}`}
              >
                {currentStudent.is_online ? "Hoạt động" : "Không hoạt động"}
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
                  value={currentStudent.email}
                />
                <InfoRow
                  icon={Calendar}
                  label="Ngày sinh"
                  value={formatDate(currentStudent.date_of_birth)}
                />
                <InfoRow
                  icon={Users}
                  label="Giới tính"
                  value={genderLabel(currentStudent.gender)}
                />
                <InfoRow
                  icon={MapPin}
                  label="Trường"
                  value={currentStudent.school_name || "Chưa cập nhật"}
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
                  value={statusLabel(currentStudent.status)}
                />
                <SystemRow
                  label="Ngày gia nhập"
                  value={formatDate(currentStudent.created_at)}
                />
                <SystemRow
                  label="Đăng nhập cuối"
                  value={formatDateTime(currentStudent.last_login_at)}
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
                ["attempts", "Bài làm"],
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
              ) : activeTab === "attempts" ? (
                <AttemptsTable detail={detail} />
              ) : activeTab === "exams" ? (
                <ExamsTable detail={detail} />
              ) : activeTab === "documents" ? (
                <DocumentsTable detail={detail} />
              ) : (
                <ActivityPanel student={currentStudent} />
              )}
            </div>
          </div>
        </div>
      </div>

      {isEditOpen && (
        <Modal
          title="Sửa thông tin học sinh"
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
          title="Xóa tài khoản học sinh"
          onClose={() => !isDeleting && setIsDeleteOpen(false)}
        >
          <div className="space-y-4">
            <p className="text-sm text-on-surface-variant">
              Xóa tài khoản {currentStudent.email}? Tài khoản sẽ bị xóa khỏi
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

function ClassesTable({ detail }: { detail: AdminStudentDetailData | null }) {
  if (!detail?.classes.length)
    return <EmptyState label="Chưa tham gia lớp học." />;
  return (
    <table className="w-full text-left border-collapse min-w-[820px]">
      <thead>
        <tr className="border-b border-outline-variant/30">
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Tên lớp
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Giáo viên
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
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Ngày tham gia
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
                {classroom.join_code}
              </p>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {classroom.teacher_name || "Chưa cập nhật"}
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
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {formatDate(classroom.joined_at)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AttemptsTable({ detail }: { detail: AdminStudentDetailData | null }) {
  if (!detail?.attempts.length) return <EmptyState label="Chưa có bài làm." />;
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
            Điểm
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Trạng thái
          </th>
          <th className="py-4 px-6 text-xs font-bold text-outline uppercase">
            Ngày nộp
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-outline-variant/20">
        {detail.attempts.map((attempt) => (
          <tr
            key={attempt.id}
            className="hover:bg-surface-variant/10 transition-colors"
          >
            <td className="py-4 px-6 font-semibold text-sm text-on-surface">
              {attempt.exam_title}
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {attempt.classroom_name || "Hệ thống"}
            </td>
            <td className="py-4 px-6 text-sm font-medium text-on-surface">
              {attempt.score ?? 0}/{attempt.total_points} (
              {formatDecimal(attempt.score_percent ?? 0, "%")})
            </td>
            <td className="py-4 px-6">
              <span
                className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold ${attempt.status === "submitted" ? "bg-[#10B981]/10 text-[#10B981]" : "bg-surface-variant text-on-surface-variant"}`}
              >
                {attempt.status === "submitted" ? "Đã nộp" : "Đang làm"}
              </span>
            </td>
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {formatDateTime(attempt.submitted_at)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ExamsTable({ detail }: { detail: AdminStudentDetailData | null }) {
  if (!detail?.exams.length)
    return <EmptyState label="Chưa có đề thi trong lớp." />;
  return (
    <table className="w-full text-left border-collapse min-w-[760px]">
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
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function DocumentsTable({ detail }: { detail: AdminStudentDetailData | null }) {
  if (!detail?.documents.length)
    return <EmptyState label="Chưa có tài liệu khả dụng." />;
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
            Giáo viên
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
            <td className="py-4 px-6 text-sm text-on-surface-variant">
              {document.teacher_name || "Hệ thống"}
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

function ActivityPanel({ student }: { student: AdminStudent }) {
  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
      <SystemTile
        label="Trạng thái tài khoản"
        value={statusLabel(student.status)}
      />
      <SystemTile
        label="Ngày gia nhập"
        value={formatDateTime(student.created_at)}
      />
      <SystemTile
        label="Đăng nhập cuối"
        value={formatDateTime(student.last_login_at)}
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
