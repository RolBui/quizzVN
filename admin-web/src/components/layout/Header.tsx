import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlignLeft,
  Bell,
  CheckCircle2,
  Download,
  FileText,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  Settings,
  Sun,
  Upload,
  User,
  UserPlus,
} from "lucide-react";
import type { ChatConversation } from "../../lib/api";
import englishFlag from "../../assets/usa.png";
import japanFlag from "../../assets/japan.jpg";
import chinaFlag from "../../assets/china.jpg";
import vietnamFlag from "../../assets/vietnam.png";
import {
  type AppNotification,
  type AppNotificationType,
  useAppNotifications,
} from "../../lib/app-notifications";
import { useAuth } from "../../lib/auth";
import { useChatNotifications } from "../../lib/chat-notifications";
import {
  GENERAL_SETTINGS_KEY,
  type AppLanguage,
  useLanguage,
} from "../../lib/language";

interface HeaderProps {
  isPinned: boolean;
  onTogglePin?: () => void;
  onOpenMobileMenu?: () => void;
}

const headerLanguageOptions: Array<{
  value: AppLanguage;
  label: string;
  flag: string;
}> = [
  { value: "vi", label: "Tiếng Việt", flag: vietnamFlag },
  { value: "en", label: "English", flag: englishFlag },
  { value: "ja", label: "Tiếng Nhật", flag: japanFlag },
  { value: "zh-CN", label: "Tiếng Trung", flag: chinaFlag },
];

function chatNotificationName(
  conversation: ChatConversation,
  currentUserId: number | undefined,
) {
  if (conversation.title) {
    return conversation.title;
  }
  const peer = conversation.participants.find(
    (participant) => participant.id !== currentUserId,
  );
  return peer?.full_name || "Cuộc trò chuyện";
}

function formatNotificationTime(value: string | null | undefined) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function notificationIcon(type: AppNotificationType) {
  const icons = {
    admin: UserPlus,
    document_import: Upload,
    document_export: Download,
    data_export: FileText,
    system: CheckCircle2,
  };
  return icons[type] ?? CheckCircle2;
}

function AppNotificationRow({ item }: { item: AppNotification }) {
  const Icon = notificationIcon(item.type);

  return (
    <div
      className={`px-4 py-3 flex items-start gap-3 transition-colors ${
        item.read ? "" : "bg-primary/5"
      }`}
    >
      <div className="w-9 h-9 rounded-full bg-primary-fixed text-on-primary-fixed flex items-center justify-center shrink-0">
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="text-sm font-semibold text-on-surface truncate">
            {item.title}
          </p>
          <span className="text-[11px] text-outline shrink-0">
            {formatNotificationTime(item.createdAt)}
          </span>
        </div>
        {item.body && (
          <p className="text-xs text-outline mt-1 line-clamp-2">{item.body}</p>
        )}
      </div>
      {!item.read && (
        <span className="mt-1.5 h-2 w-2 rounded-full bg-primary shrink-0" />
      )}
    </div>
  );
}

export function Header({
  isPinned,
  onTogglePin,
  onOpenMobileMenu,
}: HeaderProps) {
  const { user, logout } = useAuth();
  const { language, setLanguage } = useLanguage();
  const {
    clearNotificationBadge,
    notificationConversations,
    notificationCount,
  } = useChatNotifications();
  const {
    clearNotifications,
    markNotificationsRead,
    notificationPreferences,
    notifications,
    unreadCount: appUnreadCount,
  } = useAppNotifications();
  const navigate = useNavigate();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isLanguageOpen, setIsLanguageOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() =>
    document.documentElement.classList.contains("dark"),
  );
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const languageRef = useRef<HTMLDivElement>(null);
  const notificationRef = useRef<HTMLDivElement>(null);

  const chatNotificationCount = notificationPreferences.messages
    ? notificationCount
    : 0;
  const visibleNotificationConversations = notificationPreferences.messages
    ? notificationConversations
    : [];
  const visibleAppNotifications = notifications.filter(
    (item) => notificationPreferences[item.type],
  );
  const totalNotificationCount = chatNotificationCount + appUnreadCount;
  const hasChatNotifications =
    notificationPreferences.messages &&
    (chatNotificationCount > 0 || visibleNotificationConversations.length > 0);
  const hasAnyNotifications =
    hasChatNotifications || visibleAppNotifications.length > 0;
  const notificationBadge =
    totalNotificationCount > 99 ? "99+" : String(totalNotificationCount);
  const notificationSummary =
    totalNotificationCount > 0
      ? `Bạn có ${totalNotificationCount} thông báo mới`
      : hasAnyNotifications
        ? "Thông báo gần đây"
        : "Chưa có thông báo mới";
  const selectedLanguage =
    headerLanguageOptions.find((item) => item.value === language) ??
    headerLanguageOptions[0];

  const initials = (user?.full_name || user?.email || "A")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((item) => item[0])
    .join("")
    .toUpperCase();

  const toggleDarkMode = () => {
    if (isDarkMode) {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("theme", "light");
      setIsDarkMode(false);
    } else {
      document.documentElement.classList.add("dark");
      localStorage.setItem("theme", "dark");
      setIsDarkMode(true);
    }
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    await logout();
    setIsLoggingOut(false);
    navigate("/login", { replace: true });
  };

  const openSettingsTab = (tab: "general" | "account") => {
    setIsProfileOpen(false);
    navigate(`/settings?tab=${tab}`);
  };

  const saveLanguagePreference = (nextLanguage: AppLanguage) => {
    try {
      const raw = localStorage.getItem(GENERAL_SETTINGS_KEY);
      const settings = raw ? JSON.parse(raw) : {};
      localStorage.setItem(
        GENERAL_SETTINGS_KEY,
        JSON.stringify({ ...settings, language: nextLanguage }),
      );
    } catch {
      localStorage.setItem(
        GENERAL_SETTINGS_KEY,
        JSON.stringify({ language: nextLanguage }),
      );
    }
  };

  const handleLanguageChange = (nextLanguage: AppLanguage) => {
    setLanguage(nextLanguage);
    saveLanguagePreference(nextLanguage);
    setIsLanguageOpen(false);
  };

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (
      savedTheme === "dark" &&
      !document.documentElement.classList.contains("dark")
    ) {
      document.documentElement.classList.add("dark");
      setIsDarkMode(true);
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsProfileOpen(false);
      }
      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target as Node)
      ) {
        setIsNotificationsOpen(false);
      }
      if (
        languageRef.current &&
        !languageRef.current.contains(event.target as Node)
      ) {
        setIsLanguageOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const openChatFromNotifications = () => {
    clearNotificationBadge();
    setIsNotificationsOpen(false);
    navigate("/chat");
  };

  const toggleNotifications = () => {
    setIsNotificationsOpen((current) => {
      const next = !current;
      if (next) {
        markNotificationsRead();
      }
      return next;
    });
    setIsProfileOpen(false);
    setIsLanguageOpen(false);
  };

  return (
    <header className="bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant shadow-(--shadow-level-1) sticky top-0 z-40 flex justify-between items-center w-full px-2 sm:px-4 md:px-6 h-14 md:h-16 shrink-0">
      <div className="flex items-center gap-2 md:gap-4 flex-1">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="md:hidden text-outline hover:bg-surface-container-low p-2 rounded-lg"
          aria-label="Mở menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <button
          onClick={onTogglePin}
          className="hidden md:flex w-10 h-10 rounded-lg hover:bg-surface-container-low items-center justify-center text-on-surface transition-colors shrink-0 outline-none mr-2 group"
          title={isPinned ? "Thu gọn menu" : "Mở rộng menu"}
        >
          <AlignLeft
            className={`w-5 h-5 text-on-surface transition-transform duration-300 ${
              isPinned ? "" : "scale-x-[-1]"
            }`}
            strokeWidth={2}
          />
        </button>
      </div>

      <div className="flex items-center gap-0.5 sm:gap-2">
        <div className="relative" ref={languageRef}>
          <button
            type="button"
            onClick={() => {
              setIsLanguageOpen((current) => !current);
              setIsNotificationsOpen(false);
              setIsProfileOpen(false);
            }}
            className="flex h-9 w-9 sm:h-10 sm:w-10 items-center justify-center rounded-lg bg-surface-container-lowest transition-colors hover:bg-surface-container-low"
            title="Ngôn ngữ"
            aria-label="Ngôn ngữ"
          >
            <img
              src={selectedLanguage.flag}
              alt={selectedLanguage.label}
              className="h-5 w-7 rounded-sm object-cover shadow-sm"
            />
          </button>

          {isLanguageOpen && (
            <div className="absolute right-0 mt-2 w-45 overflow-hidden rounded-[6px] border border-surface-variant bg-surface-container-lowest p-2 shadow-lg z-50">
              {headerLanguageOptions.map((option) => {
                const isSelected = option.value === language;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => handleLanguageChange(option.value)}
                    className={`flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left text-sm transition-colors ${
                      isSelected
                        ? "bg-primary/10 text-primary"
                        : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                    }`}
                  >
                    <img
                      src={option.flag}
                      alt=""
                      className="h-5 w-7 rounded-sm object-cover shadow-sm"
                    />
                    <span className="font-medium">{option.label}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <button
          onClick={toggleDarkMode}
          className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-outline hover:bg-surface-container-low transition-colors"
          title={isDarkMode ? "Chế độ giao diện sáng" : "Chế độ giao diện tối"}
        >
          {isDarkMode ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>

        <div className="relative" ref={notificationRef}>
          <button
            type="button"
            onClick={toggleNotifications}
            className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-outline hover:bg-surface-container-low transition-colors"
            title={
              totalNotificationCount > 0
                ? `${totalNotificationCount} thông báo mới`
                : "Không có thông báo mới"
            }
            aria-label={
              totalNotificationCount > 0
                ? `${totalNotificationCount} thông báo mới`
                : "Không có thông báo mới"
            }
          >
            <Bell className="w-5 h-5" />
            {totalNotificationCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 rounded-full bg-error text-on-error border-2 border-surface-container-lowest flex items-center justify-center text-[10px] font-bold leading-none">
                {notificationBadge}
              </span>
            )}
          </button>

          {isNotificationsOpen && (
            <div className="fixed left-2 right-2 top-14 mt-2 w-auto bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant z-50 overflow-hidden sm:absolute sm:left-auto sm:right-0 sm:top-auto sm:w-96">
              <div className="px-4 py-3 border-b border-surface-variant">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-bold text-on-surface">Thông báo</p>
                  <div className="flex items-center gap-2">
                    {visibleAppNotifications.length > 0 && (
                      <button
                        type="button"
                        onClick={clearNotifications}
                        className="text-xs font-semibold text-outline hover:text-primary"
                      >
                        Xóa
                      </button>
                    )}
                    {totalNotificationCount > 0 && (
                      <span className="min-w-5 h-5 px-1.5 rounded-full bg-error text-on-error flex items-center justify-center text-[10px] font-bold leading-none">
                        {notificationBadge}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs text-outline mt-1">
                  {notificationSummary}
                </p>
              </div>

              <div className="max-h-[22rem] overflow-y-auto py-1">
                {visibleAppNotifications.map((item) => (
                  <AppNotificationRow key={item.id} item={item} />
                ))}

                {hasChatNotifications && visibleAppNotifications.length > 0 && (
                  <div className="mx-4 my-1 border-t border-surface-variant" />
                )}

                {chatNotificationCount > 0 &&
                  visibleNotificationConversations.length === 0 && (
                    <div className="px-4 py-4 flex items-start gap-3">
                      <div className="w-9 h-9 rounded-full bg-primary-fixed text-on-primary-fixed flex items-center justify-center shrink-0">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-on-surface">
                          {`Bạn có ${chatNotificationCount} tin nhắn mới`}
                        </p>
                        <p className="text-xs text-outline mt-1">
                          Mở mục tin nhắn để xem nội dung mới nhất.
                        </p>
                      </div>
                    </div>
                  )}

                {visibleNotificationConversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    type="button"
                    onClick={openChatFromNotifications}
                    className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-surface-container-low transition-colors"
                  >
                    <div className="w-9 h-9 rounded-full bg-primary-fixed text-on-primary-fixed flex items-center justify-center text-xs font-bold shrink-0">
                      {chatNotificationName(conversation, user?.id)
                        .slice(0, 2)
                        .toUpperCase()}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-on-surface truncate">
                          {chatNotificationName(conversation, user?.id)}
                        </p>
                        <span className="text-[11px] text-outline shrink-0">
                          {formatNotificationTime(
                            conversation.last_message?.created_at ||
                              conversation.updated_at,
                          )}
                        </span>
                      </div>
                      <p className="text-xs text-outline truncate mt-1">
                        {conversation.last_message?.body ||
                          "Bạn có tin nhắn mới"}
                      </p>
                    </div>
                    {conversation.unread_count > 0 && (
                      <span className="min-w-5 h-5 px-1 rounded-full bg-primary text-on-primary flex items-center justify-center text-[10px] font-bold leading-none shrink-0">
                        {conversation.unread_count > 99
                          ? "99+"
                          : conversation.unread_count}
                      </span>
                    )}
                  </button>
                ))}

                {!hasAnyNotifications && (
                  <div className="px-4 py-6 text-center">
                    <div className="mx-auto w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center text-outline">
                      <Bell className="w-5 h-5" />
                    </div>
                    <p className="text-sm font-medium text-on-surface mt-3">
                      Không có thông báo mới
                    </p>
                    <p className="text-xs text-outline mt-1">
                      Tin nhắn và thao tác hệ thống sẽ xuất hiện ở đây.
                    </p>
                  </div>
                )}
              </div>

              {hasChatNotifications && (
                <div className="p-2 border-t border-surface-variant">
                  <button
                    type="button"
                    onClick={openChatFromNotifications}
                    className="w-full h-9 rounded-lg text-sm font-semibold text-primary hover:bg-primary/10 transition-colors"
                  >
                    Xem tất cả tin nhắn
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="relative ml-1 sm:ml-2" ref={dropdownRef}>
          <button
            type="button"
            className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center overflow-hidden border border-outline-variant cursor-pointer ring-2 ring-transparent transition-all focus:ring-primary hover:ring-primary"
            onClick={() => {
              setIsProfileOpen(!isProfileOpen);
              setIsNotificationsOpen(false);
              setIsLanguageOpen(false);
            }}
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.full_name}
                className="w-full h-full object-cover"
              />
            ) : (
              <span className="text-xs font-bold text-on-secondary-container">
                {initials}
              </span>
            )}
          </button>

          {isProfileOpen && (
            <div className="absolute right-0 mt-2 w-40 bg-surface-container-lowest rounded-[6px] shadow-lg border border-surface-variant p-2 z-50">
              <div className="px-2 py-2 border-b border-surface-variant mb-1">
                <p className="text-sm font-semibold text-on-surface truncate">
                  {user?.full_name || "Admin"}
                </p>
                <p className="text-xs text-outline truncate">{user?.email}</p>
              </div>
              <button
                type="button"
                onClick={() => openSettingsTab("account")}
                className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-outline hover:bg-surface-container-low hover:text-on-surface transition-colors"
              >
                <User className="w-4 h-4" />
                <span className="font-medium">Tài khoản</span>
              </button>
              <button
                type="button"
                onClick={() => openSettingsTab("general")}
                className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-outline hover:bg-surface-container-low hover:text-on-surface transition-colors"
              >
                <Settings className="w-4 h-4" />
                <span className="font-medium">Cài đặt</span>
              </button>
              <div className="border-t border-surface-variant my-1" />
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="w-full flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-error hover:bg-error-container hover:text-on-error-container transition-colors disabled:opacity-60"
              >
                <LogOut className="w-4 h-4" />
                <span className="font-medium">
                  {isLoggingOut ? "Đang đăng xuất..." : "Đăng xuất"}
                </span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
