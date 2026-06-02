import { Bell, Lock, User, Globe, Shield } from "lucide-react";
import { useState } from "react";

export function Settings() {
  const [activeTab, setActiveTab] = useState("general");

  const tabs = [
    { id: "general", name: "Cài đặt chung", icon: Globe },
    { id: "account", name: "Tài khoản", icon: User },
    { id: "notifications", name: "Thông báo", icon: Bell },
    { id: "security", name: "Bảo mật", icon: Lock },
    { id: "roles", name: "Phân quyền", icon: Shield },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6 h-full">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Cài đặt Hệ thống</h1>
          
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 border border-surface-variant hover:bg-surface-container-low text-on-surface rounded-lg text-sm font-medium transition-colors">
            Hủy thay đổi
          </button>
          <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors shadow-sm">
            Lưu cài đặt
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-6 mt-2">
        {/* Sidebar settings */}
        <div className="w-full md:w-64 shrink-0">
          <div className="bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant overflow-hidden">
            <div className="flex flex-col p-2">
              {tabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors w-full text-left ${
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-outline hover:bg-surface-container-low hover:text-on-surface"
                    }`}
                  >
                    <tab.icon className={`w-5 h-5 ${isActive ? "text-primary" : "text-outline"}`} />
                    {tab.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 bg-surface-container-lowest rounded-xl shadow-(--shadow-level-1) border border-surface-variant p-6">
          {activeTab === "general" && (
            <div className="flex flex-col gap-6">
              <div>
                <h2 className="text-lg font-bold text-on-surface mb-4">Cài đặt chung</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">Tên tổ chức</label>
                    <input
                      type="text"
                      defaultValue="Hệ thống Giáo dục EduCore"
                      className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">Email liên hệ hệ thống</label>
                    <input
                      type="email"
                      defaultValue="admin@educore.edu.vn"
                      className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="w-full h-px bg-surface-variant"></div>

              <div>
                <h3 className="text-md font-semibold text-on-surface mb-3">Thông tin và Định dạng</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">Ngôn ngữ mặc định</label>
                    <select className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                      <option>Tiếng Việt</option>
                      <option>English</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">Múi giờ</label>
                    <select className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                      <option>(GMT+07:00) Bangkok, Hanoi, Jakarta</option>
                      <option>(GMT+08:00) Beijing, Singapore</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-semibold text-on-surface">Định dạng ngày</label>
                    <select className="w-full px-4 py-2 bg-surface-container-low border border-outline-variant rounded-lg text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none">
                      <option>DD/MM/YYYY</option>
                      <option>MM/DD/YYYY</option>
                      <option>YYYY-MM-DD</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "notifications" && (
            <div className="flex flex-col gap-6">
              <h2 className="text-lg font-bold text-on-surface mb-2">Thông báo email và hệ thống</h2>
              
              <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center p-4 border border-surface-variant rounded-lg">
                  <div>
                    <h3 className="text-sm font-semibold text-on-surface">Đăng ký mới</h3>
                    <p className="text-xs text-outline mt-1">Thông báo khi có tài khoản học sinh, giáo viên đăng ký mới.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" value="" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-surface-variant peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="flex justify-between items-center p-4 border border-surface-variant rounded-lg">
                  <div>
                    <h3 className="text-sm font-semibold text-on-surface">Cập nhật hệ thống</h3>
                    <p className="text-xs text-outline mt-1">Nhận email khi có bản cập nhật LMS mới.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" value="" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-surface-variant peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                <div className="flex justify-between items-center p-4 border border-surface-variant rounded-lg">
                  <div>
                    <h3 className="text-sm font-semibold text-on-surface">Báo cáo tuần</h3>
                    <p className="text-xs text-outline mt-1">Email tổng hợp hoạt động thống kê mỗi tuần.</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" value="" className="sr-only peer" />
                    <div className="w-11 h-6 bg-surface-variant peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </div>
            </div>
          )}

          {activeTab !== "general" && activeTab !== "notifications" && (
            <div className="flex h-64 flex-col items-center justify-center text-center">
              <div className="w-16 h-16 bg-surface-container mb-4 rounded-full flex items-center justify-center">
                <Shield className="w-8 h-8 text-outline" />
              </div>
              <h3 className="text-lg font-bold text-on-surface">Đang phát triển</h3>
              <p className="text-sm text-outline mt-2 max-w-sm">Mục cài đặt này đang được cập nhật. Vui lòng quay lại sau.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
