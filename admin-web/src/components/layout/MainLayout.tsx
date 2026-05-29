import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { ChatNotificationsProvider } from "../../lib/chat-notifications";

export default function MainLayout() {
  const [isSidebarPinned, setIsSidebarPinned] = useState(true);

  return (
    <div className="flex bg-background min-h-screen font-sans text-on-surface">
      <ChatNotificationsProvider>
        <Sidebar isPinned={isSidebarPinned} />
        <div
          className={`flex-1 flex flex-col min-w-0 transition-[margin] duration-250 ease-[cubic-bezier(0.4,0,0.2,1)] ${
            isSidebarPinned ? "md:ml-[260px]" : "md:ml-[88px]"
          }`}
        >
          <Header isPinned={isSidebarPinned} onTogglePin={() => setIsSidebarPinned(!isSidebarPinned)} />
          <main className="flex-1 overflow-x-hidden overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </ChatNotificationsProvider>
    </div>
  );
}
