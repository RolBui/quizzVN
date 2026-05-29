import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import { useChatNotifications } from "../../lib/chat-notifications";
import {
  School,
  Users,
  Shield,
  BookOpen,
  FileQuestion,
  FileText,
  Palette,
  Settings,
  MessageSquare,
  ChevronDown,
  LayoutDashboard,
} from "lucide-react";

interface SidebarProps {
  isPinned: boolean;
}

export function Sidebar({ isPinned }: SidebarProps) {
  const location = useLocation();
  const { clearNotificationBadge, notificationCount } = useChatNotifications();
  const path = location.pathname;
  const [dashboardExpanded, setDashboardExpanded] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  const isMenuExpanded = isPinned || isHovered;
  const isBrandExpanded = isPinned;
  const messageBadge =
    notificationCount > 99 ? "99+" : String(notificationCount);

  const routes = [
    { name: "Giáo viên", path: "/teachers", icon: School },
    { name: "Học sinh", path: "/students", icon: Users },
    { name: "Quản trị viên", path: "/admins", icon: Shield },
    { name: "Lớp học", path: "/classes", icon: BookOpen },
    { name: "Bài thi", path: "/exams", icon: FileQuestion },
    { name: "Tài liệu", path: "/documents", icon: FileText },
    { name: "Giao diện", path: "/appearance", icon: Palette },
    { name: "Cài đặt", path: "/settings", icon: Settings },
    { name: "Nhắn tin", path: "/chat", icon: MessageSquare },
  ];

  const dashboardRoutes = [
    { name: "CRM", path: "/" },
    { name: "Analytics", path: "/analytics" },
  ];

  return (
    <aside
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "fixed left-0 top-0 z-50 hidden h-screen bg-surface-container-lowest will-change-[width] transition-[width] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] md:block",
        isPinned ? "w-[260px]" : "w-[88px]",
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
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-sm font-black text-on-primary">
          Q
        </div>
        <div
          className={cn(
            "ml-3 flex flex-col justify-center overflow-hidden whitespace-nowrap transition-[width,opacity] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)]",
            isBrandExpanded ? "w-[170px] opacity-100" : "w-0 opacity-0",
          )}
        >
          <h1 className="text-lg font-black text-on-surface leading-tight">
            QuizzVN Admin
          </h1>
          <p className="text-[11px] text-outline font-medium tracking-wide">
            Hệ thống Quản lý Học tập
          </p>
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
          const badgeCount = route.path === "/chat" ? notificationCount : 0;
          return (
            <Link
              key={route.name}
              to={route.path}
              onClick={
                route.path === "/chat" ? clearNotificationBadge : undefined
              }
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
      </nav>
    </aside>
  );
}
