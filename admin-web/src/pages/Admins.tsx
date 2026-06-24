import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Check,
  Inbox,
  Loader2,
  Lock,
  Mail,
  MessageSquare,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "react-toastify";
import {
  adminApi,
  ApiError,
  chatApi,
  type AdminAccount,
  type AdminInvitation,
} from "../lib/api";
import {
  defaultAdminPermissions,
  normalizePermissions,
  permissionOptions,
  type AdminPermissionKey,
} from "../lib/admin-permissions";
import { useAppNotifications } from "../lib/app-notifications";
import { useAuth } from "../lib/auth";
import { useNavigate } from "react-router-dom";
import { PaginationBar } from "../components/PaginationBar";

const PAGE_SIZE = 7;

interface AdminFormState {
  email: string;
}

const emptyForm: AdminFormState = {
  email: "",
};

const permissionLabelByKey = new Map<AdminPermissionKey, string>(
  permissionOptions.map((option) => [option.key, option.label] as const),
);

function getInitials(account: AdminAccount) {
  return account.full_name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0])
    .join("")
    .toUpperCase();
}

function formatDate(value: string | null) {
  if (!value) {
    return "Chưa từng";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function roleLabel(roleName: string) {
  return roleName === "administrator" ? "Administrator" : "Admin";
}

function activityLabel(admin: AdminAccount) {
  if (admin.status !== "active") {
    return "Vô hiệu hóa";
  }
  return admin.is_online ? "Hoạt động" : "Không hoạt động";
}

function activityClass(admin: AdminAccount) {
  if (admin.status !== "active") {
    return "badge-destructive";
  }

  return admin.is_online ? "badge-success" : "badge-secondary";
}

function getPermissionTagLabels(admin: AdminAccount) {
  if (admin.role_name !== "admin") {
    return ["Toàn quyền"];
  }

  return normalizePermissions(admin.admin_permissions).map(
    (permission) => permissionLabelByKey.get(permission) ?? permission,
  );
}

function invitationStatusLabel(status: AdminInvitation["status"]) {
  switch (status) {
    case "otp_pending":
      return "Chờ xác thực OTP";
    case "pending_approval":
      return "Chờ duyệt";
    case "approved":
      return "Đã duyệt";
    case "rejected":
      return "Đã từ chối";
    case "expired":
      return "Hết hạn";
    default:
      return status;
  }
}

function invitationStatusClass(status: AdminInvitation["status"]) {
  switch (status) {
    case "pending_approval":
      return "badge-warning";
    case "approved":
      return "badge-success";
    case "rejected":
    case "expired":
      return "badge-destructive";
    default:
      return "badge-secondary";
  }
}

export function Admins() {
  const { user } = useAuth();
  const { addNotification } = useAppNotifications();
  const navigate = useNavigate();
  const canManageAdmins = user?.role_name === "administrator";
  const [admins, setAdmins] = useState<AdminAccount[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [invitations, setInvitations] = useState<AdminInvitation[]>([]);
  const [isInvitationModalOpen, setIsInvitationModalOpen] = useState(false);
  const [isLoadingInvitations, setIsLoadingInvitations] = useState(false);
  const [invitationError, setInvitationError] = useState<string | null>(null);
  const [invitationActionId, setInvitationActionId] = useState<string | null>(
    null,
  );
  const [deletingAdmin, setDeletingAdmin] = useState<AdminAccount | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [openingChatAdminId, setOpeningChatAdminId] = useState<number | null>(
    null,
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [form, setForm] = useState<AdminFormState>(emptyForm);
  const [permissionAdmin, setPermissionAdmin] = useState<AdminAccount | null>(
    null,
  );
  const [isSavingPermissions, setIsSavingPermissions] = useState(false);
  const [permissionDraft, setPermissionDraft] = useState<AdminPermissionKey[]>(
    defaultAdminPermissions,
  );

  const loadAdmins = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminApi.listAccounts();
      setAdmins(response.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Bạn không có quyền xem danh sách quản trị viên.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Không lấy được danh sách quản trị viên.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const loadInvitations = async () => {
    if (!canManageAdmins) {
      return;
    }

    setIsLoadingInvitations(true);
    setInvitationError(null);
    try {
      const response = await adminApi.listInvitations();
      setInvitations(response.items);
    } catch (err) {
      setInvitationError(
        err instanceof Error
          ? err.message
          : "Không lấy được danh sách lời mời.",
      );
    } finally {
      setIsLoadingInvitations(false);
    }
  };

  useEffect(() => {
    if (user) {
      void loadAdmins();
      if (canManageAdmins) {
        void loadInvitations();
      }
    }
  }, [user?.id, canManageAdmins]);

  const filteredAdmins = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return admins;
    }
    return admins.filter((admin) => {
      const permissionSearchText = getPermissionTagLabels(admin)
        .join(" ")
        .toLowerCase();

      return (
        admin.full_name.toLowerCase().includes(normalizedQuery) ||
        admin.email.toLowerCase().includes(normalizedQuery) ||
        admin.role_name.toLowerCase().includes(normalizedQuery) ||
        permissionSearchText.includes(normalizedQuery)
      );
    });
  }, [admins, query]);

  const totalPages = Math.max(1, Math.ceil(filteredAdmins.length / PAGE_SIZE));
  const paginatedAdmins = useMemo(() => {
    const startIndex = (currentPage - 1) * PAGE_SIZE;
    return filteredAdmins.slice(startIndex, startIndex + PAGE_SIZE);
  }, [currentPage, filteredAdmins]);

  useEffect(() => {
    setCurrentPage(1);
  }, [query]);

  useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  const activeCount = admins.filter(
    (admin) => admin.status === "active" && admin.is_online,
  ).length;
  const delegatedAdminCount = admins.filter(
    (admin) => admin.role_name === "admin",
  ).length;
  const disabledCount = admins.filter(
    (admin) => admin.status !== "active",
  ).length;
  const pendingApprovalInvitations = invitations.filter(
    (invitation) => invitation.status === "pending_approval",
  );
  const openInvitationCount = invitations.filter((invitation) =>
    ["otp_pending", "pending_approval"].includes(invitation.status),
  ).length;

  const openInvitationModal = () => {
    if (!canManageAdmins) {
      return;
    }
    setIsInvitationModalOpen(true);
    void loadInvitations();
  };

  const closeInvitationModal = () => {
    if (invitationActionId) {
      return;
    }
    setIsInvitationModalOpen(false);
    setInvitationError(null);
  };

  const openCreateModal = () => {
    if (!canManageAdmins) {
      return;
    }
    setIsCreateModalOpen(true);
    setForm(emptyForm);
    setFormError(null);
  };

  const closeModal = () => {
    if (isSubmitting) {
      return;
    }
    setIsCreateModalOpen(false);
    setForm(emptyForm);
    setFormError(null);
  };

  const openDeleteModal = (admin: AdminAccount) => {
    if (!canManageAdmins) {
      return;
    }
    setDeletingAdmin(admin);
    setDeleteError(null);
    setError(null);
  };

  const openPermissionDrawer = (admin: AdminAccount) => {
    if (!canManageAdmins) {
      return;
    }
    setPermissionAdmin(admin);
    setPermissionDraft(normalizePermissions(admin.admin_permissions));
  };

  const closePermissionDrawer = () => {
    if (isSavingPermissions) {
      return;
    }
    setPermissionAdmin(null);
    setPermissionDraft(defaultAdminPermissions);
  };

  const togglePermission = (permission: AdminPermissionKey) => {
    setPermissionDraft((current) =>
      current.includes(permission)
        ? current.filter((item) => item !== permission)
        : [...current, permission],
    );
  };

  const savePermissions = async () => {
    if (!permissionAdmin) {
      return;
    }
    setIsSavingPermissions(true);
    try {
      const response = await adminApi.updatePermissions(
        permissionAdmin.id,
        permissionDraft,
      );
      const savedPermissions = normalizePermissions(
        response.admin.admin_permissions,
      );
      setAdmins((current) =>
        current.map((admin) =>
          admin.id === response.admin.id
            ? { ...response.admin, admin_permissions: savedPermissions }
            : admin,
        ),
      );
      toast.success("Đã lưu phân quyền quản trị viên.");
      setPermissionAdmin(null);
      setPermissionDraft(defaultAdminPermissions);
    } catch {
      // apiRequest already shows a failure toast for API errors.
    } finally {
      setIsSavingPermissions(false);
    }
  };

  const closeDeleteModal = () => {
    if (isDeleting) {
      return;
    }
    setDeletingAdmin(null);
    setDeleteError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);
    setIsSubmitting(true);

    try {
      const response = await adminApi.createInvitation({
        email: form.email,
      });

      addNotification({
        type: "admin",
        title: "Đã gửi lời mời quản trị viên",
        body: `${response.invitation.email} đã được gửi email xác thực OTP.`,
      });
      closeModal();
      await Promise.all([loadAdmins(), loadInvitations()]);
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.message);
      } else if (err instanceof Error) {
        setFormError(err.message);
      } else {
        setFormError("Không lưu được tài khoản admin.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const approveInvitation = async (invitation: AdminInvitation) => {
    const actionId = `approve:${invitation.id}`;
    setInvitationActionId(actionId);
    setInvitationError(null);
    try {
      await adminApi.approveInvitation(invitation.id, defaultAdminPermissions);
      toast.success("Đã duyệt lời mời quản trị viên.");
      await Promise.all([loadAdmins(), loadInvitations()]);
    } catch (err) {
      setInvitationError(
        err instanceof Error ? err.message : "Không duyệt được lời mời.",
      );
    } finally {
      setInvitationActionId(null);
    }
  };

  const rejectInvitation = async (invitation: AdminInvitation) => {
    const actionId = `reject:${invitation.id}`;
    setInvitationActionId(actionId);
    setInvitationError(null);
    try {
      await adminApi.rejectInvitation(invitation.id);
      toast.success("Đã từ chối lời mời quản trị viên.");
      await loadInvitations();
    } catch (err) {
      setInvitationError(
        err instanceof Error ? err.message : "Không từ chối được lời mời.",
      );
    } finally {
      setInvitationActionId(null);
    }
  };

  const handleDelete = async () => {
    if (!deletingAdmin) {
      return;
    }

    setError(null);
    setDeleteError(null);
    setIsDeleting(true);
    try {
      await adminApi.deleteAccount(deletingAdmin.id);
      setDeletingAdmin(null);
      await loadAdmins();
    } catch (err) {
      if (err instanceof Error) {
        setDeleteError(err.message);
      } else {
        setDeleteError("Không xóa được tài khoản admin.");
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const openAdminChat = async (admin: AdminAccount) => {
    if (openingChatAdminId || admin.id === user?.id) {
      return;
    }

    setError(null);
    setOpeningChatAdminId(admin.id);
    try {
      const response = await chatApi.createConversation(admin.id);
      navigate("/chat", {
        state: { conversationId: response.conversation.id },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể mở tin nhắn.");
    } finally {
      setOpeningChatAdminId(null);
    }
  };

  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-lg font-bold text-on-surface">Quản trị viên</h1>
        </div>
        {canManageAdmins && (
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <button
              type="button"
              onClick={openInvitationModal}
              className="relative w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-2 text-sm font-medium text-on-surface shadow-sm transition-colors hover:bg-surface-container-low sm:w-auto"
            >
              <span className="flex items-center justify-center gap-2">
                <Inbox className="w-4 h-4" />
                Lời mời
              </span>
              {openInvitationCount > 0 && (
                <span className="absolute -right-2 -top-2 min-w-5 rounded-full bg-error px-1.5 py-0.5 text-xs font-bold leading-none text-on-error">
                  {pendingApprovalInvitations.length || openInvitationCount}
                </span>
              )}
            </button>
          <button
            onClick={openCreateModal}
            className="w-full px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 shadow-sm sm:w-auto"
          >
            <Plus className="w-4 h-4" /> Thêm quản trị viên
          </button>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-error-container bg-error-container/60 px-4 py-3 flex items-start gap-3 text-sm text-on-error-container">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div>
            <p className="text-sm text-on-surface font-medium">
              Tổng quản trị viên
            </p>
            <p className="text-3xl font-bold text-on-surface mt-1">
              {admins.length}
            </p>
            <div className="text-xs text-primary font-medium mt-2 flex items-center gap-1">
              {delegatedAdminCount} admin được cấp quyền
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div>
            <p className="text-sm text-on-surface-variant font-medium">
              Đang hoạt động
            </p>
            <p className="text-3xl font-bold text-on-surface mt-1">
              {activeCount}
            </p>
            <div className="text-xs text-on-surface-variant mt-2">
              Có tương tác trong 1 giờ qua
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div>
            <p className="text-sm text-on-surface-variant font-medium">
              Vô hiệu hóa
            </p>
            <p className="text-3xl font-bold text-on-surface mt-1">
              {disabledCount}
            </p>
            <div className="text-xs text-error font-medium mt-2 flex items-center gap-1">
              <Mail className="w-3 h-3" /> Không thể đăng nhập
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) overflow-hidden">
        <div className="p-4 border-b border-surface-variant flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm theo tên, email, vai trò hoặc tag..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left border-collapse">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-low/30">
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Quản trị viên
                </th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Vai trò
                </th>
                <th className="w-80 min-w-72 py-3 px-6 text-center text-xs font-semibold text-on-surface-variant">
                  Tag
                </th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Đăng nhập cuối
                </th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Trạng thái
                </th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant text-right">
                  Thao tác
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {isLoading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="py-8 px-6 text-center text-sm text-on-surface-variant"
                  >
                    Đang tải danh sách admin...
                  </td>
                </tr>
              ) : filteredAdmins.length > 0 ? (
                paginatedAdmins.map((admin) => {
                  const permissionTags = getPermissionTagLabels(admin);

                  return (
                    <tr
                      key={admin.id}
                      className="hover:bg-surface-container-lowest/50 transition-colors"
                    >
                      <td className="py-4 px-6 flex items-center gap-3">
                        {admin.avatar_url ? (
                          <img
                            src={admin.avatar_url}
                            alt={admin.full_name}
                            className="w-10 h-10 rounded-full object-cover"
                          />
                        ) : (
                          <div className="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center font-bold text-sm">
                            {getInitials(admin)}
                          </div>
                        )}
                        <div>
                          <p className="text-sm font-semibold text-on-surface">
                            {admin.full_name}
                          </p>
                          <p className="text-xs text-outline font-medium">
                            {admin.email}
                          </p>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm text-on-surface font-medium">
                        {roleLabel(admin.role_name)}
                      </td>
                      <td className="w-80 min-w-72 py-4 px-6 text-center">
                        {permissionTags.length > 0 ? (
                          <div className="mx-auto flex max-w-72 flex-wrap justify-center gap-1.5">
                            {permissionTags.map((tag) => (
                              <span key={tag} className="badge badge-secondary">
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span className="text-xs italic text-outline">
                            Chưa phân quyền
                          </span>
                        )}
                      </td>
                      <td
                        className={`py-4 px-6 ${admin.last_login_at ? "text-sm text-on-surface" : "text-xs italic text-outline"}`}
                      >
                        {formatDate(admin.last_login_at)}
                      </td>
                      <td className="py-4 px-6">
                        <span className={`badge ${activityClass(admin)}`}>
                          {activityLabel(admin)}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right">
                        {admin.role_name === "admin" ? (
                          <div className="inline-flex items-center gap-1">
                            {canManageAdmins && (
                              <button
                                onClick={() => openPermissionDrawer(admin)}
                                className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors"
                                title="Phân quyền"
                              >
                                <ShieldCheck className="w-4 h-4" />
                              </button>
                            )}
                            <button
                              onClick={() => void openAdminChat(admin)}
                              disabled={openingChatAdminId === admin.id}
                              className="text-outline hover:text-primary p-2 rounded hover:bg-surface-container-low transition-colors disabled:opacity-60"
                              title="Nhắn tin"
                            >
                              {openingChatAdminId === admin.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <MessageSquare className="w-4 h-4" />
                              )}
                            </button>
                            {canManageAdmins && (
                              <button
                                onClick={() => openDeleteModal(admin)}
                                className="text-outline hover:text-error p-2 rounded hover:bg-error-container transition-colors"
                                title="Xóa admin"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        ) : (
                          <span className="text-xs text-outline">
                            Tài khoản gốc
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td
                    colSpan={6}
                    className="py-8 px-6 text-center text-sm text-on-surface-variant"
                  >
                    Không có quản trị viên phù hợp
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <PaginationBar
          page={currentPage}
          pageSize={PAGE_SIZE}
          totalItems={filteredAdmins.length}
          onPageChange={setCurrentPage}
        />
      </div>

      {permissionAdmin && (
        <div className="fixed inset-0 z-[90] flex justify-end bg-black/35 backdrop-blur-[2px]">
          <button
            type="button"
            aria-label="Đóng form phân quyền"
            className="hidden md:block flex-1 cursor-default"
            onClick={closePermissionDrawer}
          />
          <aside className="flex h-full w-full max-w-xl flex-col bg-surface-container-lowest shadow-(--shadow-level-2)">
            <div className="border-b border-outline-variant px-6 py-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-bold text-on-surface">
                    Phân quyền quản trị viên
                  </h2>
                  <p className="mt-3 max-w-md text-sm leading-6 text-on-surface-variant">
                    Chọn các khu vực mà quản trị viên này được phép quản lý
                    trong hệ thống.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closePermissionDrawer}
                  disabled={isSavingPermissions}
                  className="rounded-lg p-2 text-outline transition-colors hover:bg-surface-container-low hover:text-on-surface"
                  aria-label="Đóng"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-8">
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-wide text-outline">
                  Tên quản trị viên
                </span>
                <div className="relative mt-3">
                  <input
                    value={permissionAdmin.full_name}
                    readOnly
                    className="h-12 w-full rounded-lg border border-outline-variant bg-surface-container-low px-4 pr-11 text-sm font-medium text-on-surface outline-none"
                  />
                  <Lock className="absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-outline" />
                </div>
              </label>

              <div className="mt-10">
                <p className="text-xs font-bold uppercase tracking-wide text-outline">
                  Phạm vi quản lý
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  {permissionOptions.map((option) => {
                    const isSelected = permissionDraft.includes(option.key);
                    return (
                      <button
                        key={option.key}
                        type="button"
                        onClick={() => togglePermission(option.key)}
                        className={`inline-flex min-h-11 items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                          isSelected
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-outline-variant bg-surface-container-lowest text-on-surface-variant hover:border-primary/60 hover:text-primary"
                        }`}
                      >
                        {isSelected && <Check className="h-4 w-4" />}
                        <span>{option.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="border-t border-outline-variant bg-surface-container-low px-6 py-5">
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={closePermissionDrawer}
                  disabled={isSavingPermissions}
                  className="h-11 rounded-lg px-6 text-sm font-semibold text-on-surface transition-colors hover:bg-surface-container-high disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Hủy
                </button>
                <button
                  type="button"
                  onClick={() => void savePermissions()}
                  disabled={isSavingPermissions}
                  className="h-11 rounded-lg bg-primary px-6 text-sm font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSavingPermissions ? "Đang lưu..." : "Lưu phân quyền"}
                </button>
              </div>
            </div>
          </aside>
        </div>
      )}

      {isInvitationModalOpen && (
        <div className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-5xl bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-on-surface">
                  Lời mời quản trị viên
                </h2>
                <p className="mt-1 text-sm text-outline">
                  Theo dõi ai đã gửi lời mời và các yêu cầu đang chờ duyệt.
                </p>
              </div>
              <button
                type="button"
                onClick={closeInvitationModal}
                disabled={Boolean(invitationActionId)}
                className="p-2 rounded-lg hover:bg-surface-container-low text-outline disabled:opacity-60"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-wrap gap-2 text-sm">
                  <span className="badge badge-warning">
                    {pendingApprovalInvitations.length} chờ duyệt
                  </span>
                  <span className="badge badge-secondary">
                    {openInvitationCount} đang mở
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => void loadInvitations()}
                  disabled={isLoadingInvitations || Boolean(invitationActionId)}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-outline-variant px-4 text-sm font-medium text-on-surface transition-colors hover:bg-surface-container-low disabled:opacity-60"
                >
                  {isLoadingInvitations && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  Tải lại
                </button>
              </div>

              {invitationError && (
                <div className="rounded-lg border border-error-container bg-error-container/60 px-3 py-2 flex items-start gap-2 text-sm text-on-error-container">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{invitationError}</span>
                </div>
              )}

              <div className="max-h-[60vh] overflow-auto rounded-xl border border-outline-variant">
                <table className="w-full min-w-[900px] text-left border-collapse">
                  <thead>
                    <tr className="border-b border-surface-variant bg-surface-container-low/50">
                      <th className="py-3 px-4 text-xs font-semibold text-on-surface-variant">
                        Người nhận
                      </th>
                      <th className="py-3 px-4 text-xs font-semibold text-on-surface-variant">
                        Người gửi
                      </th>
                      <th className="py-3 px-4 text-xs font-semibold text-on-surface-variant">
                        Trạng thái
                      </th>
                      <th className="py-3 px-4 text-xs font-semibold text-on-surface-variant">
                        Thời gian
                      </th>
                      <th className="py-3 px-4 text-xs font-semibold text-on-surface-variant text-right">
                        Thao tác
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-variant">
                    {isLoadingInvitations ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-8 px-4 text-center text-sm text-on-surface-variant"
                        >
                          Đang tải danh sách lời mời...
                        </td>
                      </tr>
                    ) : invitations.length > 0 ? (
                      invitations.map((invitation) => {
                        const approveActionId = `approve:${invitation.id}`;
                        const rejectActionId = `reject:${invitation.id}`;
                        const isActing =
                          invitationActionId === approveActionId ||
                          invitationActionId === rejectActionId;
                        const inviter =
                          invitation.invited_by_name ||
                          invitation.invited_by_email ||
                          "Không rõ";

                        return (
                          <tr
                            key={invitation.id}
                            className="hover:bg-surface-container-lowest/50"
                          >
                            <td className="py-4 px-4">
                              <p className="text-sm font-semibold text-on-surface">
                                {invitation.full_name || invitation.email}
                              </p>
                              <p className="text-xs text-outline">
                                {invitation.email}
                              </p>
                            </td>
                            <td className="py-4 px-4">
                              <p className="text-sm font-medium text-on-surface">
                                {inviter}
                              </p>
                              {invitation.invited_by_name &&
                                invitation.invited_by_email && (
                                  <p className="text-xs text-outline">
                                    {invitation.invited_by_email}
                                  </p>
                                )}
                            </td>
                            <td className="py-4 px-4">
                              <span
                                className={`badge ${invitationStatusClass(invitation.status)}`}
                              >
                                {invitationStatusLabel(invitation.status)}
                              </span>
                            </td>
                            <td className="py-4 px-4 text-sm text-on-surface">
                              {formatDate(invitation.created_at)}
                            </td>
                            <td className="py-4 px-4 text-right">
                              {invitation.status === "pending_approval" ? (
                                <div className="inline-flex items-center gap-2">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void approveInvitation(invitation)
                                    }
                                    disabled={Boolean(invitationActionId)}
                                    className="inline-flex h-9 items-center gap-2 rounded-lg bg-primary px-3 text-xs font-semibold text-on-primary transition-colors hover:bg-primary/90 disabled:opacity-60"
                                  >
                                    {invitationActionId === approveActionId && (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    )}
                                    Duyệt
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void rejectInvitation(invitation)
                                    }
                                    disabled={Boolean(invitationActionId)}
                                    className="inline-flex h-9 items-center gap-2 rounded-lg border border-error-container px-3 text-xs font-semibold text-error transition-colors hover:bg-error-container disabled:opacity-60"
                                  >
                                    {invitationActionId === rejectActionId && (
                                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                    )}
                                    Từ chối
                                  </button>
                                </div>
                              ) : isActing ? (
                                <Loader2 className="ml-auto h-4 w-4 animate-spin text-outline" />
                              ) : (
                                <span className="text-xs text-outline">
                                  Không cần xử lý
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td
                          colSpan={5}
                          className="py-8 px-4 text-center text-sm text-on-surface-variant"
                        >
                          Chưa có lời mời quản trị viên nào.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {deletingAdmin && (
        <div className="fixed inset-0 z-[90] bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-md bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full bg-error-container text-on-error-container flex items-center justify-center shrink-0">
                  <Trash2 className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-on-surface">
                    Xóa quản trị viên
                  </h2>
                  <p className="text-sm text-outline mt-1">
                    Hành động này không thể hoàn tác.
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
                void handleDelete();
              }}
              className="p-5 space-y-4"
            >
              <div className="rounded-lg border border-error-container bg-error-container/40 px-4 py-3">
                <p className="text-sm text-on-surface">
                  Bạn có chắc muốn xóa tài khoản admin này?
                </p>
                <p className="text-sm font-semibold text-on-surface mt-2">
                  {deletingAdmin.full_name}
                </p>
                <p className="text-xs text-outline mt-1">
                  {deletingAdmin.email}
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
                  Xóa quản trị viên
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {isCreateModalOpen && (
        <div className="fixed inset-0 z-80 bg-black/35 flex items-center justify-center px-4">
          <div className="w-full max-w-115 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-(--shadow-level-2)">
            <div className="px-5 py-4 border-b border-outline-variant flex items-center justify-between">
              <h2 className="text-lg font-bold text-on-surface">
                Thêm quản trị viên
              </h2>
              <button
                onClick={closeModal}
                className="p-2 rounded-lg hover:bg-surface-container-low text-outline"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              {formError && (
                <div className="rounded-lg border border-error-container bg-error-container/60 px-3 py-2 flex items-start gap-2 text-sm text-on-error-container">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{formError}</span>
                </div>
              )}

              <label className="block">
                <span className="text-sm font-semibold text-on-surface">
                  Email
                </span>
                <input
                  type="email"
                  value={form.email}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      email: event.target.value,
                    }))
                  }
                  required
                  className="mt-2 w-full h-10 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </label>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium text-on-surface hover:bg-surface-container-low"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-semibold hover:bg-primary/90 disabled:opacity-70 flex items-center gap-2"
                >
                  {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Thêm
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
