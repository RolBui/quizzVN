import { useState, useRef, useEffect } from "react";
import { Bell, Search, Menu, User, Settings, Lock, LogOut, AlignLeft, Moon, Sun } from "lucide-react";

interface HeaderProps {
  isPinned: boolean;
  onTogglePin?: () => void;
}

export function Header({ isPinned, onTogglePin }: HeaderProps) {
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => document.documentElement.classList.contains("dark"));
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    // Check initial theme from localStorage on component mount
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
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="bg-surface-container-lowest/80 backdrop-blur-md border-b border-outline-variant shadow-[var(--shadow-level-1)] sticky top-0 z-40 flex justify-between items-center w-full px-4 md:px-6 h-14 md:h-16 shrink-0">
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
            className={`w-5 h-5 text-on-surface transition-transform duration-300 ${isPinned ? "" : "scale-x-[-1]"}`} 
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
        
        <button className="relative w-10 h-10 rounded-full flex items-center justify-center text-outline hover:bg-surface-container-low transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-2 right-2.5 w-2 h-2 bg-error rounded-full border-2 border-surface-container-lowest"></span>
        </button>
        
        <div className="relative ml-2" ref={dropdownRef}>
          <div 
            className="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center overflow-hidden border border-outline-variant cursor-pointer ring-2 ring-transparent transition-all focus-within:ring-primary hover:ring-primary"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
          >
            <img
              src="https://images.unsplash.com/photo-1560250097-0b93528c311a?w=100&h=100&fit=crop"
              alt="Profile"
              className="w-full h-full object-cover"
            />
          </div>

          {isProfileOpen && (
            <div className="absolute right-0 mt-2 w-48 bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant py-2 z-50">
              <div className="px-4 py-2 border-b border-surface-variant mb-1">
                <p className="text-sm font-semibold text-on-surface">Xin chào!</p>
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
              <div className="border-t border-surface-variant my-1"></div>
              <button className="w-full flex items-center gap-3 px-4 py-2 text-sm text-error hover:bg-error-container hover:text-on-error-container transition-colors">
                <LogOut className="w-4 h-4" />
                <span className="font-medium">Đăng xuất</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
