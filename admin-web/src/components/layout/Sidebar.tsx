import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
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
  AlignLeft
} from "lucide-react";

interface SidebarProps {
  isPinned: boolean;
}

export function Sidebar({ isPinned }: SidebarProps) {
  const location = useLocation();
  const path = location.pathname;
  const [dashboardExpanded, setDashboardExpanded] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  const isExpanded = isPinned || isHovered;

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
    { name: "Analytics", path: "/analytics" }
  ];

  return (
    <aside 
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={cn(
        "fixed left-0 top-0 h-screen z-50 border-r border-outline-variant bg-surface-container-lowest hidden md:flex flex-col py-4 gap-2 transition-all duration-300 ease-in-out",
        isExpanded ? "w-[260px] shadow-lg shadow-black/5" : "w-[88px]"
      )}
    >
      <div className={cn("flex items-center shrink-0 mb-4 h-16 transition-all duration-300", isExpanded ? "px-6" : "px-0 justify-center")}>
        <div className="w-10 h-10 rounded-xl bg-primary-container text-on-primary-container flex items-center justify-center font-bold text-xl shrink-0 transition-all">
          E
        </div>
        <div 
           className={cn(
             "flex flex-col justify-center overflow-hidden whitespace-nowrap transition-all duration-300", 
             isExpanded ? "w-[150px] opacity-100 ml-3" : "w-0 opacity-0 ml-0"
           )}
        >
          <h1 className="text-lg font-black text-on-surface leading-tight">EduCore Admin</h1>
          <p className="text-[11px] text-outline font-medium tracking-wide">Hệ thống Quản lý Học tập</p>
        </div>
      </div>
      
      <nav className={cn(
        "flex flex-col gap-1 flex-1 overflow-x-hidden overflow-y-auto pb-4 transition-all duration-300",
        isExpanded ? "px-4" : "px-4"
      )}>
        <div 
          className={cn(
            "text-[11px] font-bold text-outline uppercase tracking-wider transition-all duration-300",
            isExpanded ? "px-3 opacity-100 max-h-[20px] mt-2 mb-2" : "max-h-0 opacity-0 overflow-hidden m-0"
          )}
        >
          Menu
        </div>
        <div className={cn("transition-all duration-300", isExpanded ? "mb-1" : "mb-0")}>
          <button
            onClick={() => setDashboardExpanded(!dashboardExpanded)}
            className={cn(
               "w-full flex items-center h-[40px] rounded-lg transition-colors group overflow-hidden whitespace-nowrap",
               isExpanded ? "px-3" : "justify-center",
               path === "/" || path === "/analytics" ? "text-sidebar-active-text font-semibold" : "text-outline hover:bg-surface-container-low hover:text-on-surface"
            )}
            title={!isExpanded ? "Dashboard" : undefined}
          >
            <Settings
              strokeWidth={2}
              className={cn("w-5 h-5 shrink-0 transition-colors", path === "/" || path === "/analytics" ? "text-sidebar-active-icon" : "text-outline group-hover:text-on-surface")}
            />
            <span 
              className={cn(
                "text-sm font-semibold transition-all duration-300 text-left overflow-hidden whitespace-nowrap",
                isExpanded ? "opacity-100 ml-3 flex-1" : "opacity-0 ml-0 flex-none w-0"
              )}
            >
              Dashboard
            </span>
            <div className={cn("overflow-hidden transition-all duration-300 flex items-center justify-end", isExpanded ? "w-4 opacity-100" : "w-0 opacity-0")}>
              <ChevronDown
                className={cn(
                   "w-4 h-4 transition-transform shrink-0", 
                   path === "/" || path === "/analytics" ? "text-sidebar-active-icon" : "text-outline", 
                   dashboardExpanded ? "" : "-rotate-90"
                )}
              />
            </div>
          </button>
          
          <div 
             className={cn(
                "overflow-hidden transition-all duration-300",
                dashboardExpanded && isExpanded ? "max-h-40 mt-1" : "max-h-0 mt-0"
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
                        : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low"
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
            "text-[11px] font-bold text-outline uppercase tracking-wider transition-all duration-300",
            isExpanded ? "px-3 opacity-100 max-h-[20px] mb-2 mt-4" : "max-h-0 opacity-0 overflow-hidden m-0"
          )}
        >
          Apps
        </div>

        {routes.map((route) => {
          const isActive = path === route.path || (path.startsWith(route.path) && route.path !== "/");
          return (
            <Link
              key={route.name}
              to={route.path}
              className={cn(
                "w-full flex items-center h-[40px] rounded-lg transition-colors group overflow-hidden whitespace-nowrap",
                isExpanded ? "px-3" : "justify-center",
                isActive
                  ? "bg-sidebar-active-bg text-sidebar-active-text font-semibold"
                  : "text-outline hover:bg-surface-container-low hover:text-on-surface"
              )}
              title={!isExpanded ? route.name : undefined}
            >
              <route.icon
                strokeWidth={isActive ? 2.5 : 2}
                className={cn("w-5 h-5 shrink-0 transition-colors", isActive ? "text-sidebar-active-icon" : "text-outline group-hover:text-on-surface")}
              />
              <span 
                className={cn(
                  "text-sm transition-all duration-300 overflow-hidden whitespace-nowrap",
                  isExpanded ? "opacity-100 ml-3 flex-1" : "opacity-0 flex-none w-0 ml-0"
                )}
              >
                {route.name}
              </span>
            </Link>
          );
        })}
      </nav>

    </aside>
  );
}
