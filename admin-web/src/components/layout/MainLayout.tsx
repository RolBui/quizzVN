import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export default function MainLayout() {
  const [isSidebarPinned, setIsSidebarPinned] = useState(true);

  return (
    <div className="flex bg-background min-h-screen font-sans text-on-surface">
      <Sidebar isPinned={isSidebarPinned} />
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ${isSidebarPinned ? 'md:ml-[260px]' : 'md:ml-[88px]'}`}>
        <Header isPinned={isSidebarPinned} onTogglePin={() => setIsSidebarPinned(!isSidebarPinned)} />
        <main className="flex-1 overflow-x-hidden overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
