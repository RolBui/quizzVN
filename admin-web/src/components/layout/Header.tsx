import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlignLeft,
  Bell,
  Lock,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  Search,
  Settings,
  Sun,
  User,
} from "lucide-react";
import type { ChatConversation } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useChatNotifications } from "../../lib/chat-notifications";

interface HeaderProps {
  isPinned: boolean;
  onTogglePin?: () => void;
}

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
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function Header({ isPinned, onTogglePin }: HeaderProps) {
  const { user, logout } = useAuth();
  const {
    clearNotificationBadge,
    notificationConversations,
    notificationCount,
  } = useChatNotifications();
  const navigate = useNavigate();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() =>
    document.documentElement.classList.contains("dark"),
  );
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notificationRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "dark" && !document.documentElement.classList.contains("dark")) {
      document.documentElement.classList.add("dark");
      setIsDarkMode(true);
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileOpen(false);
      }
      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target as Node)
      ) {
        setIsNotificationsOpen(false);
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

  return (
    <header className="bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant shadow-(--shadow-level-1) sticky top-0 z-40 flex justify-between items-center w-full px-4 md:px-6 h-14 md:h-16 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <button className="md:hidden text-outline hover:bg-surface-container-low p-2 rounded-lg">
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

        <div className="relative w-full max-w-md ml-0 lg:ml-2 hidden md:flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-outline" />
          <input
            type="text"
            placeholder="Tìm kiếm trên hệ thống..."
            className="w-full bg-surface-container-low border border-outline-variant rounded-full py-2 pl-10 pr-4 text-sm text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-all placeholder:text-outline"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={toggleDarkMode}
          className="relative w-10 h-10 rounded-full flex items-center justify-center text-outline hover:bg-surface-container-low transition-colors"
          title={isDarkMode ? "Chế độ giao diện sáng" : "Chế độ giao diện tối"}
        >
          {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        <div className="relative" ref={notificationRef}>
        <button
          type="button"
          onClick={() => {
            setIsNotificationsOpen((current) => !current);
            setIsProfileOpen(false);
          }}
          className="relative w-10 h-10 rounded-full flex items-center justify-center text-outline hover:bg-surface-container-low transition-colors"
          title={
            notificationCount > 0
              ? `${notificationCount} tin nhắn mới`
              : "Không có tin nhắn mới"
          }
          aria-label={
            notificationCount > 0
              ? `${notificationCount} tin nhắn mới`
              : "Không có tin nhắn mới"
          }
        >
          <Bell className="w-5 h-5" />
          {notificationCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-5 h-5 px-1 rounded-full bg-error text-on-error border-2 border-surface-container-lowest flex items-center justify-center text-[10px] font-bold leading-none">
              {notificationCount > 99 ? "99+" : notificationCount}
            </span>
          )}
        </button>

          {isNotificationsOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-surface-variant">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-bold text-on-surface">
                    Thông báo
                  </p>
                  {notificationCount > 0 && (
                    <span className="min-w-5 h-5 px-1.5 rounded-full bg-error text-on-error flex items-center justify-center text-[10px] font-bold leading-none">
                      {notificationCount > 99 ? "99+" : notificationCount}
                    </span>
                  )}
                </div>
                <p className="text-xs text-outline mt-1">
                  {notificationCount > 0
                    ? `Bạn có ${notificationCount} tin nhắn mới`
                    : "Chưa có thông báo mới"}
                </p>
              </div>

              <div className="max-h-80 overflow-y-auto py-1">
                {notificationCount > 0 &&
                  notificationConversations.length === 0 && (
                    <div className="px-4 py-4 flex items-start gap-3">
                      <div className="w-9 h-9 rounded-full bg-primary-fixed text-on-primary-fixed flex items-center justify-center shrink-0">
                        <MessageSquare className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-on-surface">
                          Bạn có {notificationCount} tin nhắn mới
                        </p>
                        <p className="text-xs text-outline mt-1">
                          Mở mục tin nhắn để xem nội dung mới nhất.
                        </p>
                      </div>
                    </div>
                  )}

                {notificationConversations.map((conversation) => (
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

                {notificationCount === 0 && (
                  <div className="px-4 py-6 text-center">
                    <div className="mx-auto w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center text-outline">
                      <Bell className="w-5 h-5" />
                    </div>
                    <p className="text-sm font-medium text-on-surface mt-3">
                      Không có tin nhắn mới
                    </p>
                    <p className="text-xs text-outline mt-1">
                      Thông báo tin nhắn sẽ xuất hiện ở đây.
                    </p>
                  </div>
                )}
              </div>

              <div className="p-2 border-t border-surface-variant">
                <button
                  type="button"
                  onClick={openChatFromNotifications}
                  className="w-full h-9 rounded-lg text-sm font-semibold text-primary hover:bg-primary/10 transition-colors"
                >
                  Xem tất cả tin nhắn
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="relative ml-2" ref={dropdownRef}>
          <button
            type="button"
            className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center overflow-hidden border border-outline-variant cursor-pointer ring-2 ring-transparent transition-all focus:ring-primary hover:ring-primary"
            onClick={() => {
              setIsProfileOpen(!isProfileOpen);
              setIsNotificationsOpen(false);
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
            <div className="absolute right-0 mt-2 w-56 bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant py-2 z-50">
              <div className="px-4 py-2 border-b border-surface-variant mb-1">
                <p className="text-sm font-semibold text-on-surface truncate">
                  {user?.full_name || "Admin"}
                </p>
                <p className="text-xs text-outline truncate">{user?.email}</p>
              </div>
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-outline hover:bg-surface-container-low hover:text-on-surface transition-colors">
                <User className="w-4 h-4" />
                <span className="font-medium">Tài khoản</span>
              </button>
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-outline hover:bg-surface-container-low hover:text-on-surface transition-colors">
                <Settings className="w-4 h-4" />
                <span className="font-medium">Cài đặt</span>
              </button>
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-outline hover:bg-surface-container-low hover:text-on-surface transition-colors">
                <Lock className="w-4 h-4" />
                <span className="font-medium">Khóa màn hình</span>
              </button>
              <div className="border-t border-surface-variant my-1" />
              <button
                onClick={handleLogout}
                disabled={isLoggingOut}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-error hover:bg-error-container hover:text-on-error-container transition-colors disabled:opacity-60"
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
