import { Bell, ChevronDown, Globe, KeyRound, Loader2, User } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "react-toastify";
import {
  defaultNotificationPreferences,
  type NotificationPreferenceKey,
  type NotificationPreferences,
  useAppNotifications,
} from "../lib/app-notifications";
import { useAuth } from "../lib/auth";
import { authApi, type AuthUser } from "../lib/api";
import {
  GENERAL_SETTINGS_KEY,
  type AppLanguage,
  useLanguage,
} from "../lib/language";

type SettingsTab = "general" | "account" | "notifications";

interface GeneralSettings {
  language: AppLanguage;
  timezone: string;
}

interface NotificationOption {
  key: NotificationPreferenceKey;
  title: string;
  description: string;
}

interface AccountDraft {
  fullName: string;
  phone: string;
}

interface PasswordDraft {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

const defaultGeneralSettings: GeneralSettings = {
  language: "vi",
  timezone: "Asia/Ho_Chi_Minh",
};

const emptyPasswordDraft: PasswordDraft = {
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
};

const notificationOptions: NotificationOption[] = [
  {
    key: "messages",
    title: "Tin nhắn mới",
    description: "Hiện badge và thông báo khi có tin nhắn mới.",
  },
  {
    key: "admin",
    title: "Thêm quản trị viên",
    description: "Thông báo sau khi tạo tài khoản quản trị viên mới.",
  },
  {
    key: "document_import",
    title: "Nhập tài liệu",
    description: "Thông báo khi upload tài liệu PDF hoặc DOCX thành công.",
  },
  {
    key: "document_export",
    title: "Xuất tài liệu",
    description: "Thông báo khi tải tài liệu về máy.",
  },
  {
    key: "data_export",
    title: "Xuất dữ liệu",
    description: "Thông báo khi xuất danh sách học sinh hoặc giáo viên.",
  },
  {
    key: "system",
    title: "Thông báo hệ thống",
    description: "Các thông báo vận hành khác của dashboard admin.",
  },
];

const tabs: Array<{ id: SettingsTab; name: string; icon: typeof Globe }> = [
  { id: "general", name: "Cài đặt chung", icon: Globe },
  { id: "account", name: "Tài khoản", icon: User },
  { id: "notifications", name: "Thông báo", icon: Bell },
];

const languageOptions: Array<{ value: AppLanguage; label: string }> = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "English" },
  { value: "ja", label: "Tiếng Nhật" },
  { value: "zh-CN", label: "Tiếng Trung (giản thể)" },
];

const timezoneOptions = [
  {
    value: "Asia/Ho_Chi_Minh",
    label: "(GMT+07:00) Vietnam - Hanoi, Ho Chi Minh City",
  },
  {
    value: "Asia/Singapore",
    label: "(GMT+08:00) Singapore",
  },
  {
    value: "Asia/Tokyo",
    label: "(GMT+09:00) Japan - Tokyo",
  },
  {
    value: "Asia/Shanghai",
    label: "(GMT+08:00) China - Beijing, Shanghai",
  },
  {
    value: "America/Toronto",
    label: "(GMT-05:00) Canada - Toronto, Eastern Time",
  },
  {
    value: "America/Vancouver",
    label: "(GMT-08:00) Canada - Vancouver, Pacific Time",
  },
  {
    value: "America/New_York",
    label: "(GMT-05:00) USA - New York, Eastern Time",
  },
  {
    value: "America/Chicago",
    label: "(GMT-06:00) USA - Chicago, Central Time",
  },
  {
    value: "America/Denver",
    label: "(GMT-07:00) USA - Denver, Mountain Time",
  },
  {
    value: "America/Los_Angeles",
    label: "(GMT-08:00) USA - Los Angeles, Pacific Time",
  },
];

function readGeneralSettings() {
  if (typeof window === "undefined") {
    return defaultGeneralSettings;
  }

  try {
    const raw = window.localStorage.getItem(GENERAL_SETTINGS_KEY);
    if (!raw) {
      return defaultGeneralSettings;
    }
    const settings = {
      ...defaultGeneralSettings,
      ...(JSON.parse(raw) as Partial<GeneralSettings>),
    };
    return {
      ...settings,
      timezone:
        settings.timezone === "Asia/Bangkok"
          ? "Asia/Ho_Chi_Minh"
          : settings.timezone,
    };
  } catch {
    return defaultGeneralSettings;
  }
}

function saveGeneralSettings(settings: GeneralSettings) {
  window.localStorage.setItem(GENERAL_SETTINGS_KEY, JSON.stringify(settings));
}

function readTabFromSearch(value: string | null): SettingsTab {
  if (value === "account" || value === "notifications") {
    return value;
  }
  return "general";
}

function getInitials(value: string | null | undefined) {
  return (value || "A")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0])
    .join("")
    .toUpperCase();
}

function getRoleLabel(role: string | null | undefined) {
  if (role === "administrator") {
    return "Administrator";
  }
  if (role === "admin") {
    return "Admin";
  }
  return role || "Chưa cập nhật";
}

function getLocaleForLanguage(language: AppLanguage) {
  const locales: Record<AppLanguage, string> = {
    vi: "vi-VN",
    en: "en-US",
    ja: "ja-JP",
    "zh-CN": "zh-CN",
  };
  return locales[language];
}

function getAccountDraft(user: AuthUser | null | undefined): AccountDraft {
  return {
    fullName: user?.full_name || "",
    phone: user?.phone || "",
  };
}

function isEqual(left: unknown, right: unknown) {
  return JSON.stringify(left) === JSON.stringify(right);
}

function NotificationSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
        checked ? "bg-primary" : "bg-surface-variant"
      }`}
    >
      <span
        className={`absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

export function Settings() {
  const { refreshSession, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const { notificationPreferences, replaceNotificationPreferences } =
    useAppNotifications();
  const { setLanguage } = useLanguage();
  const [activeTab, setActiveTab] = useState<SettingsTab>(() =>
    readTabFromSearch(tabParam),
  );
  const [savedGeneralSettings, setSavedGeneralSettings] =
    useState<GeneralSettings>(readGeneralSettings);
  const [draftGeneralSettings, setDraftGeneralSettings] =
    useState<GeneralSettings>(savedGeneralSettings);
  const [savedNotificationPreferences, setSavedNotificationPreferences] =
    useState<NotificationPreferences>(notificationPreferences);
  const [draftNotificationPreferences, setDraftNotificationPreferences] =
    useState<NotificationPreferences>({
      ...defaultNotificationPreferences,
      ...notificationPreferences,
    });
  const [isEditingAccount, setIsEditingAccount] = useState(false);
  const [isSavingAccount, setIsSavingAccount] = useState(false);
  const [accountDraft, setAccountDraft] = useState<AccountDraft>(() =>
    getAccountDraft(user),
  );
  const [passwordDraft, setPasswordDraft] =
    useState<PasswordDraft>(emptyPasswordDraft);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const hasChanges = useMemo(
    () =>
      !isEqual(draftGeneralSettings, savedGeneralSettings) ||
      !isEqual(draftNotificationPreferences, savedNotificationPreferences),
    [
      draftGeneralSettings,
      draftNotificationPreferences,
      savedGeneralSettings,
      savedNotificationPreferences,
    ],
  );

  const hasAccountChanges = useMemo(() => {
    const current = getAccountDraft(user);
    return (
      accountDraft.fullName.trim() !== current.fullName.trim() ||
      accountDraft.phone.trim() !== current.phone.trim()
    );
  }, [accountDraft, user]);

  const isPasswordFormReady =
    passwordDraft.currentPassword.length > 0 &&
    passwordDraft.newPassword.length > 0 &&
    passwordDraft.confirmPassword.length > 0;

  const updateGeneralSetting = (key: keyof GeneralSettings, value: string) => {
    setDraftGeneralSettings((current) => ({
      ...current,
      [key]: key === "language" ? (value as AppLanguage) : value,
    }));
  };

  const updateNotificationPreference = (
    key: NotificationPreferenceKey,
    enabled: boolean,
  ) => {
    setDraftNotificationPreferences((current) => ({
      ...current,
      [key]: enabled,
    }));
  };

  const updateAccountDraft = (key: keyof AccountDraft, value: string) => {
    setAccountDraft((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const updatePasswordDraft = (key: keyof PasswordDraft, value: string) => {
    setPasswordDraft((current) => ({
      ...current,
      [key]: value,
    }));
  };

  const handleCancel = () => {
    setDraftGeneralSettings(savedGeneralSettings);
    setDraftNotificationPreferences(savedNotificationPreferences);
    setLanguage(savedGeneralSettings.language);
  };

  useEffect(() => {
    if (!isEditingAccount) {
      setAccountDraft(getAccountDraft(user));
    }
  }, [isEditingAccount, user]);

  useEffect(() => {
    const nextTab = readTabFromSearch(tabParam);
    if (activeTab === nextTab) {
      return;
    }
    setDraftGeneralSettings(savedGeneralSettings);
    setDraftNotificationPreferences(savedNotificationPreferences);
    setLanguage(savedGeneralSettings.language);
    setActiveTab(nextTab);
  }, [
    activeTab,
    savedGeneralSettings,
    savedNotificationPreferences,
    setLanguage,
    tabParam,
  ]);

  const handleSave = () => {
    saveGeneralSettings(draftGeneralSettings);
    replaceNotificationPreferences(draftNotificationPreferences);
    setSavedGeneralSettings(draftGeneralSettings);
    setSavedNotificationPreferences(draftNotificationPreferences);
    setLanguage(draftGeneralSettings.language);
  };

  const handleAccountSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isEditingAccount) {
      setIsEditingAccount(true);
      return;
    }
    const fullName = accountDraft.fullName.trim();
    if (!fullName) {
      toast.error("Họ tên không được để trống.");
      return;
    }
    setIsSavingAccount(true);
    try {
      await authApi.updateProfile({
        full_name: fullName,
        phone: accountDraft.phone.trim() || null,
      });
      await refreshSession();
      setAccountDraft({
        fullName,
        phone: accountDraft.phone.trim(),
      });
      setIsEditingAccount(false);
      toast.success("Đã lưu thông tin tài khoản.");
    } catch {
      // apiRequest already shows a failure toast for API errors.
    } finally {
      setIsSavingAccount(false);
    }
  };

  const handlePasswordSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!isPasswordFormReady) {
      toast.error("Vui lòng nhập đầy đủ thông tin đổi mật khẩu.");
      return;
    }
    if (passwordDraft.newPassword.length < 6) {
      toast.error("Mật khẩu mới phải có ít nhất 6 ký tự.");
      return;
    }
    if (passwordDraft.newPassword !== passwordDraft.confirmPassword) {
      toast.error("Mật khẩu mới không khớp.");
      return;
    }

    setIsChangingPassword(true);
    try {
      const response = await authApi.changePassword({
        current_password: passwordDraft.currentPassword,
        new_password: passwordDraft.newPassword,
        confirm_password: passwordDraft.confirmPassword,
      });
      setPasswordDraft(emptyPasswordDraft);
      toast.success(response.message || "Đã đổi mật khẩu.");
    } catch {
      // apiRequest already shows a failure toast for API errors.
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleTabChange = (tab: SettingsTab) => {
    if (tab === activeTab) {
      return;
    }
    handleCancel();
    setIsEditingAccount(false);
    setAccountDraft(getAccountDraft(user));
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const formatAccountDate = (value: string | null | undefined) => {
    if (!value) {
      return "Chưa có";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "Chưa có";
    }
    return new Intl.DateTimeFormat(
      getLocaleForLanguage(draftGeneralSettings.language),
      {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      },
    ).format(date);
  };

  const accountDetails = [
    { label: "Vai trò", value: getRoleLabel(user?.role_name) },
    { label: "Tên đăng nhập", value: user?.username || "Chưa cập nhật" },
    { label: "Email", value: user?.email || "Chưa cập nhật" },
    { label: "Số điện thoại", value: user?.phone || "Chưa cập nhật" },
    {
      label: "Đăng nhập gần nhất",
      value: formatAccountDate(user?.last_login_at),
    },
    { label: "Ngày tạo", value: formatAccountDate(user?.created_at) },
  ];

  return (
    <div className="p-4 flex flex-col gap-4 h-full">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-lg md:text-xl font-semibold text-on-surface">
            Cài đặt Hệ thống
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={!hasChanges}
            className="h-10 px-5 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
          >
            Lưu cài đặt
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 mt-2">
        <div className="w-full md:w-64 shrink-0">
          <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant overflow-hidden">
            <div className="flex flex-col p-2">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => handleTabChange(tab.id)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors w-full text-left ${
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-outline hover:bg-surface-container-low hover:text-on-surface"
                    }`}
                  >
                    <tab.icon
                      className={`w-5 h-5 ${isActive ? "text-primary" : "text-outline"}`}
                    />
                    {tab.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="flex-1 bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant p-5">
          {activeTab === "general" && (
            <div className="flex flex-col gap-4">
              <div>
                <h2 className="text-lg font-bold text-on-surface mb-4">
                  Thông tin và Định dạng
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">
                      Ngôn ngữ mặc định
                    </label>
                    <div className="relative">
                      <select
                        value={draftGeneralSettings.language}
                        onChange={(event) =>
                          updateGeneralSetting("language", event.target.value)
                        }
                        className="w-full appearance-none px-4 py-2 pr-10 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none cursor-pointer"
                      >
                        {languageOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                    </div>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">
                      Múi giờ
                    </label>
                    <div className="relative">
                      <select
                        value={draftGeneralSettings.timezone}
                        onChange={(event) =>
                          updateGeneralSetting("timezone", event.target.value)
                        }
                        className="w-full appearance-none px-4 py-2 pr-10 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none cursor-pointer"
                      >
                        {timezoneOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-on-surface" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "account" && (
            <div className="flex flex-col gap-4">
              <form
                onSubmit={handleAccountSubmit}
                className="flex flex-col gap-4"
              >
              <div>
                <h2 className="text-lg font-bold text-on-surface">
                  Thông tin tài khoản
                </h2>
                <p className="mt-1 text-sm text-outline">
                  Thông tin tài khoản quản trị viên đang đăng nhập.
                </p>
              </div>

              <div className="flex flex-col gap-4 rounded-lg border border-surface-variant p-5 md:flex-row md:items-center">
                <div className="relative h-20 w-20 shrink-0">
                  <div className="h-full w-full overflow-hidden rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center text-2xl font-bold border border-outline-variant">
                    {user?.avatar_url ? (
                      <img
                        src={user.avatar_url}
                        alt={user.full_name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      getInitials(user?.full_name || user?.email)
                    )}
                  </div>
                  {user?.status === "active" && (
                    <span className="absolute bottom-2 right-1 h-4 w-4 rounded-full border-2 border-surface-container-lowest bg-[#10B981]" />
                  )}
                </div>
                <div className="min-w-0">
                  {isEditingAccount ? (
                    <label className="block">
                      <span className="sr-only">Họ tên</span>
                      <input
                        value={accountDraft.fullName}
                        onChange={(event) =>
                          updateAccountDraft("fullName", event.target.value)
                        }
                        className="w-full max-w-md rounded-lg border border-outline-variant bg-surface-container-low px-3 py-2 text-xl font-bold text-on-surface outline-none focus:border-primary"
                        placeholder="Họ tên"
                      />
                    </label>
                  ) : (
                    <h3 className="text-xl font-bold text-on-surface truncate">
                      {user?.full_name || "Administrator"}
                    </h3>
                  )}
                  <p className="mt-1 text-sm text-outline truncate">
                    {user?.email || "Chưa cập nhật"}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {accountDetails.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-lg border border-surface-variant bg-surface-container-lowest px-4 py-3"
                  >
                    <p className="text-xs font-semibold uppercase text-outline">
                      {item.label}
                    </p>
                    {isEditingAccount && item.label === "Số điện thoại" ? (
                      <input
                        value={accountDraft.phone}
                        onChange={(event) =>
                          updateAccountDraft("phone", event.target.value)
                        }
                        className="mt-1 w-full rounded-md border border-outline-variant bg-surface-container-low px-3 py-2 text-sm font-semibold text-on-surface outline-none focus:border-primary"
                        placeholder="Số điện thoại"
                      />
                    ) : (
                      <p className="mt-1 text-sm font-semibold text-on-surface break-words">
                        {item.value}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={
                    isSavingAccount || (isEditingAccount && !hasAccountChanges)
                  }
                  className="h-10 px-5 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary/90 transition-colors shadow-sm disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isEditingAccount
                    ? isSavingAccount
                      ? "Đang lưu..."
                      : "Lưu thông tin"
                    : "Sửa thông tin"}
                </button>
              </div>
              </form>

              <form
                onSubmit={handlePasswordSubmit}
                className="flex flex-col gap-4 border-t border-surface-variant pt-5"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <KeyRound className="h-5 w-5 text-primary" />
                    <h3 className="text-base font-bold text-on-surface">
                      Đổi mật khẩu
                    </h3>
                  </div>
                  <p className="mt-1 text-sm text-outline">
                    Dùng mật khẩu tạm hoặc mật khẩu hiện tại để đặt mật khẩu mới dễ đăng nhập hơn.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-semibold text-on-surface">
                      Mật khẩu hiện tại
                    </span>
                    <input
                      type="password"
                      value={passwordDraft.currentPassword}
                      onChange={(event) =>
                        updatePasswordDraft("currentPassword", event.target.value)
                      }
                      autoComplete="current-password"
                      className="h-11 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      placeholder="Nhập mật khẩu hiện tại"
                    />
                  </label>
                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-semibold text-on-surface">
                      Mật khẩu mới
                    </span>
                    <input
                      type="password"
                      value={passwordDraft.newPassword}
                      onChange={(event) =>
                        updatePasswordDraft("newPassword", event.target.value)
                      }
                      autoComplete="new-password"
                      className="h-11 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      placeholder="Tối thiểu 6 ký tự"
                    />
                  </label>
                  <label className="flex flex-col gap-2">
                    <span className="text-sm font-semibold text-on-surface">
                      Nhập lại mật khẩu mới
                    </span>
                    <input
                      type="password"
                      value={passwordDraft.confirmPassword}
                      onChange={(event) =>
                        updatePasswordDraft("confirmPassword", event.target.value)
                      }
                      autoComplete="new-password"
                      className="h-11 rounded-lg border border-outline-variant bg-surface-container-low px-3 text-sm text-on-surface outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      placeholder="Nhập lại mật khẩu mới"
                    />
                  </label>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isChangingPassword || !isPasswordFormReady}
                    className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-sm font-semibold text-on-primary shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isChangingPassword && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    {isChangingPassword ? "Đang đổi..." : "Đổi mật khẩu"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="flex flex-col gap-4">
              <div>
                <h2 className="text-lg font-bold text-on-surface">
                  Thông báo trong hệ thống
                </h2>
                <p className="mt-1 text-sm text-outline">
                  Bật hoặc tắt từng loại thông báo xuất hiện ở chuông góc trên.
                </p>
              </div>

              <div className="flex flex-col gap-3">
                {notificationOptions.map((option) => (
                  <div
                    key={option.key}
                    className="flex items-center justify-between gap-4 rounded-lg border border-surface-variant px-4 py-4"
                  >
                    <div className="min-w-0">
                      <h3 className="text-sm font-semibold text-on-surface">
                        {option.title}
                      </h3>
                      <p className="text-xs text-outline mt-1">
                        {option.description}
                      </p>
                    </div>
                    <NotificationSwitch
                      checked={draftNotificationPreferences[option.key]}
                      onChange={(checked) =>
                        updateNotificationPreference(option.key, checked)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
