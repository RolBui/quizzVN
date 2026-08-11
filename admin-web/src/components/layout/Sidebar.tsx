import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import {
  useAdminPermissions,
  type AdminPermissionKey,
} from "../../lib/admin-permissions";
import { useAuth } from "../../lib/auth";
import { useChatNotifications } from "../../lib/chat-notifications";
import { useAppNotifications } from "../../lib/app-notifications";
import quizzvnLogo from "../../assets/logo quizzvn.png";
import quizzvnLogoSmall from "../../assets/logoquizzsmall.png";
import {
  School,
  Users,
  Shield,
  BookOpen,
  FileQuestion,
  FileText,
  Settings,
  MessageSquare,
  ChevronDown,
  LayoutDashboard,
  AlertTriangle,
} from "lucide-react";

interface SidebarProps {
  isPinned: boolean;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface SidebarRoute {
  name: string;
  path: string;
  icon: typeof School;
  permission?: AdminPermissionKey;
}

export function Sidebar({
  isPinned,
  isMobileOpen = false,
  onMobileClose,
}: SidebarProps) {
  const location = useLocation();
  const { user } = useAuth();
  const { clearNotificationBadge, notificationCount } = useChatNotifications();
  const { notificationPreferences } = useAppNotifications();
  const path = location.pathname;
  const [dashboardExpanded, setDashboardExpanded] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  const isMenuExpanded = isMobileOpen || isPinned || isHovered;
  const isBrandExpanded = isMobileOpen || isPinned;
  const messageBadge =
    notificationCount > 99 ? "99+" : String(notificationCount);

  const permissions = useAdminPermissions(user);
  const showPermissionNotice =
    user?.role_name === "admin" && permissions.length === 0;

  const allRoutes: SidebarRoute[] = [
    {
      name: "Giáo viên",
      path: "/teachers",
      icon: School,
      permission: "teachers",
    },
    {
      name: "Học sinh",
      path: "/students",
      icon: Users,
      permission: "students",
    },
    {
      name: "Quản trị viên",
      path: "/admins",
      icon: Shield,
      permission: "admins",
    },
    {
      name: "Lớp học",
      path: "/classes",
      icon: BookOpen,
      permission: "classes",
    },
    {
      name: "Bài thi",
      path: "/exams",
      icon: FileQuestion,
      permission: "exams",
    },
    {
      name: "Tài liệu",
      path: "/documents",
      icon: FileText,
      permission: "documents",
    },
    { name: "Nhắn tin", path: "/chat", icon: MessageSquare },
    { name: "Cài đặt", path: "/settings", icon: Settings },
  ];
  const routes = allRoutes.filter(
    (route) => !route.permission || permissions.includes(route.permission),
  );

  const dashboardRoutes = [
    { name: "Tổng quan", path: "/" },
    { name: "Phân tích dữ liệu", path: "/analytics" },
  ];

  return (
    <>
      {isMobileOpen && (
        <button
          type="button"
          aria-label="Đóng menu"
          onClick={onMobileClose}
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-[1px] md:hidden"
        />
      )}
      <aside
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          "fixed left-0 top-0 z-50 h-dvh w-[260px] bg-surface-container-lowest will-change-[width,transform] transition-[width,transform] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
          isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          isPinned ? "md:w-[260px]" : "md:w-[88px]",
        )}
      >
        <div
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute bottom-0 right-0 top-0 z-10 w-px bg-outline-variant transition-opacity duration-150",
            !isPinned && isHovered ? "opacity-0" : "opacity-100",
          )}
        />
        <div
          className={cn(
            "flex h-16 shrink-0 items-center border-b border-outline-variant bg-surface-container-lowest transition-[padding,width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
            isBrandExpanded ? "w-[260px] px-6" : "w-[88px] justify-center px-0",
          )}
        >
          <div
            className={cn(
              "flex h-12 shrink-0 items-center overflow-hidden rounded-md transition-[width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
              isBrandExpanded
                ? "w-[205px] justify-start"
                : "w-11 justify-center",
            )}
          >
            <img
              src={isBrandExpanded ? quizzvnLogo : quizzvnLogoSmall}
              alt="QuizzVN"
              className={cn(
                "h-full transition-[width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
                isBrandExpanded
                  ? "w-[205px] max-w-none object-cover object-[50%_54%]"
                  : "w-11 object-contain",
              )}
            />
          </div>
        </div>

        <nav
          className={cn(
            "absolute bottom-0 left-0 top-16 flex flex-col gap-1 overflow-x-hidden overflow-y-auto bg-surface-container-lowest pb-4 transition-[width,padding,box-shadow] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
            isMenuExpanded
              ? "w-[260px] px-4 shadow-lg shadow-black/5"
              : "w-[88px] px-4",
            !isPinned && isHovered ? "border-r border-outline-variant" : "",
          )}
        >
          <div
            className={cn(
              "text-[11px] font-bold text-outline uppercase tracking-wider transition-[max-height,opacity,margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
              isMenuExpanded
                ? "px-3 opacity-100 max-h-[20px] mt-2 mb-2"
                : "max-h-0 opacity-0 overflow-hidden m-0",
            )}
          >
            Danh mục
          </div>
          <div
            className={cn(
              "transition-[margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
              isMenuExpanded ? "mb-1" : "mb-0",
            )}
          >
            <button
              onClick={() => setDashboardExpanded(!dashboardExpanded)}
              className={cn(
                "w-full flex items-center h-[40px] rounded-lg transition-colors group overflow-hidden whitespace-nowrap",
                isMenuExpanded ? "px-3" : "justify-center",
                path === "/" || path === "/analytics"
                  ? "text-sidebar-active-text font-semibold"
                  : "text-outline hover:bg-surface-container-low hover:text-on-surface",
              )}
              title={!isMenuExpanded ? "Bảng điều khiển" : undefined}
            >
              <LayoutDashboard
                strokeWidth={2}
                className={cn(
                  "w-5 h-5 shrink-0 transition-colors",
                  path === "/" || path === "/analytics"
                    ? "text-sidebar-active-icon"
                    : "text-outline group-hover:text-on-surface",
                )}
              />
              <span
                className={cn(
                  "text-sm font-semibold transition-[opacity,margin,width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] text-left overflow-hidden whitespace-nowrap",
                  isMenuExpanded
                    ? "opacity-100 ml-3 flex-1"
                    : "opacity-0 ml-0 flex-none w-0",
                )}
              >
                Bảng điều khiển
              </span>
              <div
                className={cn(
                  "overflow-hidden transition-[width,opacity] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] flex items-center justify-end",
                  isMenuExpanded ? "w-4 opacity-100" : "w-0 opacity-0",
                )}
              >
                <ChevronDown
                  className={cn(
                    "w-4 h-4 transition-transform shrink-0",
                    path === "/" || path === "/analytics"
                      ? "text-sidebar-active-icon"
                      : "text-outline",
                    dashboardExpanded ? "" : "-rotate-90",
                  )}
                />
              </div>
            </button>

            <div
              className={cn(
                "overflow-hidden transition-[max-height,margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
                dashboardExpanded && isMenuExpanded
                  ? "max-h-40 mt-1"
                  : "max-h-0 mt-0",
              )}
            >
              <div className="flex flex-col gap-1 pr-0 pl-[32px]">
                {dashboardRoutes.map((route) => {
                  const isActive = path === route.path;
                  return (
                    <Link
                      key={route.name}
                      to={route.path}
                      onClick={onMobileClose}
                      className={cn(
                        "flex items-center px-3 h-[40px] rounded-lg transition-colors text-sm truncate whitespace-nowrap",
                        isActive
                          ? "bg-sidebar-active-bg text-sidebar-active-text font-medium"
                          : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low",
                      )}
                    >
                      {route.name}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          <div
            className={cn(
              "text-[11px] font-bold text-outline uppercase tracking-wider transition-[max-height,opacity,margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
              isMenuExpanded
                ? "px-3 opacity-100 max-h-[20px] mb-2 mt-4"
                : "max-h-0 opacity-0 overflow-hidden m-0",
            )}
          >
            Quản lý
          </div>

          {routes.map((route) => {
            const isActive =
              path === route.path ||
              (path.startsWith(route.path) && route.path !== "/");
            const badgeCount =
              route.path === "/chat" && notificationPreferences.messages
                ? notificationCount
                : 0;
            return (
              <Link
                key={route.name}
                to={route.path}
                onClick={() => {
                  if (route.path === "/chat") {
                    clearNotificationBadge();
                  }
                  onMobileClose?.();
                }}
                className={cn(
                  "relative w-full flex items-center h-[40px] rounded-lg transition-colors group overflow-hidden whitespace-nowrap",
                  isMenuExpanded ? "px-3" : "justify-center",
                  isActive
                    ? "bg-sidebar-active-bg text-sidebar-active-text font-semibold"
                    : "text-outline hover:bg-surface-container-low hover:text-on-surface",
                )}
                title={!isMenuExpanded ? route.name : undefined}
              >
                <route.icon
                  strokeWidth={isActive ? 2.5 : 2}
                  className={cn(
                    "w-5 h-5 shrink-0 transition-colors",
                    isActive
                      ? "text-sidebar-active-icon"
                      : "text-outline group-hover:text-on-surface",
                  )}
                />
                {!isMenuExpanded && badgeCount > 0 && (
                  <span className="absolute top-1 right-2 min-w-5 h-5 px-1 rounded-full bg-error text-on-error border-2 border-surface-container-lowest flex items-center justify-center text-[10px] font-bold leading-none">
                    {messageBadge}
                  </span>
                )}
                <span
                  className={cn(
                    "text-sm transition-[opacity,margin,width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] overflow-hidden whitespace-nowrap",
                    isMenuExpanded
                      ? "opacity-100 ml-3 flex-1"
                      : "opacity-0 flex-none w-0 ml-0",
                  )}
                >
                  {route.name}
                </span>
                {isMenuExpanded && badgeCount > 0 && (
                  <span className="ml-2 min-w-5 h-5 px-1.5 rounded-full bg-error text-on-error flex items-center justify-center text-[10px] font-bold leading-none shrink-0">
                    {messageBadge}
                  </span>
                )}
              </Link>
            );
          })}
          {showPermissionNotice && (
            <div
              className={cn(
                "mt-auto overflow-hidden transition-[max-height,opacity,padding] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
                isMenuExpanded
                  ? "max-h-52 pt-4 opacity-100"
                  : "max-h-0 p-0 opacity-0",
              )}
            >
              <div className="rounded-[4px] border border-amber-200 bg-amber-50 px-3 py-3 text-amber-900 shadow-sm">
                <div className="flex items-center gap-2 text-sm font-bold leading-5">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
                  <span>Thông báo !</span>
                </div>
                <p className="mt-2 text-xs font-medium leading-5 text-amber-900">
                  Bạn chưa được phân quyền điều hành các chức năng chính.
                </p>
                <p className="mt-1 text-xs font-medium leading-5 text-amber-900">
                  Hãy liên hệ Administrator để phân quyền !
                </p>
              </div>
            </div>
          )}
        </nav>
      </aside>
    </>
  );
}
