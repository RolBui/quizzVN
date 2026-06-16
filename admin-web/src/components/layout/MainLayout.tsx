import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { ChatNotificationsProvider } from "../../lib/chat-notifications";
import { AppNotificationsProvider } from "../../lib/app-notifications";

export default function MainLayout() {
  const [isSidebarPinned, setIsSidebarPinned] = useState(true);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  useEffect(() => {
    if (!isMobileSidebarOpen) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isMobileSidebarOpen]);

  return (
    <div className="flex bg-background min-h-screen font-sans text-on-surface">
      <AppNotificationsProvider>
        <ChatNotificationsProvider>
          <Sidebar
            isPinned={isSidebarPinned}
            isMobileOpen={isMobileSidebarOpen}
            onMobileClose={() => setIsMobileSidebarOpen(false)}
          />
          <div
            className={`flex-1 flex flex-col min-w-0 transition-[margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] ${
              isSidebarPinned ? "md:ml-[260px]" : "md:ml-[88px]"
            }`}
          >
            <Header
              isPinned={isSidebarPinned}
              onTogglePin={() => setIsSidebarPinned(!isSidebarPinned)}
              onOpenMobileMenu={() => setIsMobileSidebarOpen(true)}
            />
            <main className="flex-1 overflow-x-hidden overflow-y-auto">
              <Outlet />
            </main>
          </div>
        </ChatNotificationsProvider>
      </AppNotificationsProvider>
    </div>
  );
}
