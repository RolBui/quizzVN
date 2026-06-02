import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Loader2,
  Mail,
  MessageSquare,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import {
  adminApi,
  ApiError,
  chatApi,
  type AdminAccount,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { useNavigate } from "react-router-dom";
import { PaginationBar } from "../components/PaginationBar";

const PAGE_SIZE = 7;

interface AdminFormState {
  full_name: string;
  email: string;
  password: string;
}

const emptyForm: AdminFormState = {
  full_name: "",
  email: "",
  password: "",
};

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
    return "bg-[#EF4444]/10 text-[#EF4444]";
  }

  return admin.is_online
    ? "bg-[#10B981]/10 text-[#10B981]"
    : "bg-surface-variant text-on-surface-variant";
}

export function Admins() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const canManageAdmins = user?.role_name === "administrator";
  const [admins, setAdmins] = useState<AdminAccount[]>([]);
  const [query, setQuery] = useState("");
  const [isLoading, setIsLoading] = useState(canManageAdmins);
  const [error, setError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [deletingAdmin, setDeletingAdmin] = useState<AdminAccount | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [openingChatAdminId, setOpeningChatAdminId] = useState<number | null>(
    null,
  );
  const [currentPage, setCurrentPage] = useState(1);
  const [form, setForm] = useState<AdminFormState>(emptyForm);

  const loadAdmins = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await adminApi.listAccounts();
      setAdmins(response.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Chỉ Administrator mới được quản lý tài khoản admin.");
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Không lấy được danh sách quản trị viên.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (canManageAdmins) {
      void loadAdmins();
    }
  }, [canManageAdmins]);

  const filteredAdmins = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) {
      return admins;
    }
    return admins.filter((admin) => {
      return (
        admin.full_name.toLowerCase().includes(normalizedQuery) ||
        admin.email.toLowerCase().includes(normalizedQuery) ||
        admin.role_name.toLowerCase().includes(normalizedQuery)
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

  const openCreateModal = () => {
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
    setDeletingAdmin(admin);
    setDeleteError(null);
    setError(null);
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
      await adminApi.createAccount({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
      });

      closeModal();
      await loadAdmins();
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

  if (!canManageAdmins) {
    return (
      <div className="p-4 md:p-6">
        <div className="rounded-xl border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-4 py-4 flex items-start gap-3 text-on-surface">
          <AlertCircle className="w-5 h-5 text-[#F59E0B] shrink-0 mt-0.5" />
          <div>
            <h1 className="text-base font-bold">
              Chỉ Administrator được quản lý admin
            </h1>
            <p className="text-sm text-on-surface-variant mt-1">
              Tài khoản admin thường chỉ được vào hệ thống, không được cấp hoặc
              thu hồi quyền admin khác.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex justify-between items-end gap-4">
        <div>
          <h1 className="text-xl font-bold text-on-surface">Quản trị viên</h1>
        </div>
        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm"
        >
          <Plus className="w-4 h-4" /> Thêm quản trị viên
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-error-container bg-error-container/60 px-4 py-3 flex items-start gap-3 text-sm text-on-error-container">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-(--shadow-level-1) border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div>
            <p className="text-sm text-on-surface-variant font-medium">
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
              placeholder="Tìm theo tên, email hoặc vai trò..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-low/30">
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Quản trị viên
                </th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">
                  Vai trò
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
                    colSpan={5}
                    className="py-8 px-6 text-center text-sm text-on-surface-variant"
                  >
                    Đang tải danh sách admin...
                  </td>
                </tr>
              ) : filteredAdmins.length > 0 ? (
                paginatedAdmins.map((admin) => (
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
                    <td
                      className={`py-4 px-6 text-sm ${admin.last_login_at ? "text-on-surface" : "italic text-outline"}`}
                    >
                      {formatDate(admin.last_login_at)}
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${activityClass(admin)}`}
                      >
                        {activityLabel(admin)}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right">
                      {admin.role_name === "admin" ? (
                        <div className="inline-flex items-center gap-1">
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
                          <button
                            onClick={() => openDeleteModal(admin)}
                            className="text-outline hover:text-error p-2 rounded hover:bg-error-container transition-colors"
                            title="Xóa admin"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-outline">
                          Tài khoản gốc
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan={5}
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
                  Họ tên
                </span>
                <input
                  value={form.full_name}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      full_name: event.target.value,
                    }))
                  }
                  required
                  className="mt-2 w-full h-10 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                />
              </label>

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

              <label className="block">
                <span className="text-sm font-semibold text-on-surface">
                  Mật khẩu
                </span>
                <input
                  type="password"
                  value={form.password}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      password: event.target.value,
                    }))
                  }
                  required
                  placeholder="Tối thiểu 6 ký tự"
                  className="mt-2 w-full h-10 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary placeholder:text-outline"
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
