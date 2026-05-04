import { Download, Filter, Plus, Search, Shield, MoreHorizontal, TrendingUp, UserCheck, MailWarning, Mail } from "lucide-react";

export function Admins() {
  const admins = [
    { name: "Michael Chen", email: "m.chen@educore.edu", role: "Super Admin", department: "IT Operations", lastLogin: "2 giờ trước", status: "Hoạt động", color: "bg-[#10B981]/10 text-[#10B981]", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop" },
    { name: "Sarah Jenkins", email: "s.jenkins@educore.edu", role: "Giám đốc Học thuật", department: "Chương trình học", lastLogin: "1 ngày trước", status: "Hoạt động", color: "bg-[#10B981]/10 text-[#10B981]", avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=100&h=100&fit=crop" },
    { name: "David Ross", email: "d.ross@educore.edu", role: "Trưởng phòng Hỗ trợ", department: "Dịch vụ Học sinh", lastLogin: "Chưa từng", status: "Đang chờ", color: "bg-surface-variant text-on-surface-variant", initials: "DR" },
    { name: "Robert Fox", email: "r.fox@educore.edu", role: "Cán bộ Tuân thủ", department: "Hành chính", lastLogin: "3 tuần trước", status: "Đình chỉ", color: "bg-[#EF4444]/10 text-[#EF4444]", avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&h=100&fit=crop" },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản trị viên</h1>
          
        </div>
        <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
          <Plus className="w-4 h-4" /> Thêm Quản trị viên
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <Shield className="w-4 h-4" />
             </div>
             <MoreHorizontal className="w-5 h-5 text-outline cursor-pointer" />
          </div>
          <div>
            <p className="text-sm text-on-surface-variant font-medium">Tổng Quản trị viên</p>
            <p className="text-3xl font-bold text-on-surface mt-1">42</p>
            <div className="text-xs text-primary font-medium mt-2 flex items-center gap-1">
               <TrendingUp className="w-3 h-3"/> +3 so với tháng trước
            </div>
          </div>
        </div>
        
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <div className="w-8 h-8 rounded-full bg-secondary/10 flex items-center justify-center text-secondary">
                <UserCheck className="w-4 h-4" />
             </div>
             <MoreHorizontal className="w-5 h-5 text-outline cursor-pointer" />
          </div>
          <div>
            <p className="text-sm text-on-surface-variant font-medium">Đang hoạt động</p>
            <p className="text-3xl font-bold text-on-surface mt-1">18</p>
            <div className="text-xs text-on-surface-variant mt-2 flex items-center gap-1">
               Tại 4 phòng ban
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <div className="w-8 h-8 rounded-full bg-error/10 flex items-center justify-center text-error">
                <MailWarning className="w-4 h-4" />
             </div>
             <MoreHorizontal className="w-5 h-5 text-outline cursor-pointer" />
          </div>
          <div>
            <p className="text-sm text-on-surface-variant font-medium">Lời mời đang chờ</p>
            <p className="text-3xl font-bold text-on-surface mt-1">5</p>
            <div className="text-xs text-error font-medium mt-2 flex items-center gap-1">
               <Mail className="w-3 h-3"/> Cần theo dõi
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] overflow-hidden">
        <div className="p-4 border-b border-surface-variant flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Tìm kiếm thư mục bằng tên hoặc vai trò..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto mt-2 sm:mt-0">
             <button className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 border border-surface-variant rounded-lg text-sm text-on-surface hover:bg-surface-container-low transition-colors">
                <Filter className="w-4 h-4" /> Lọc
             </button>
             <button className="flex-1 sm:flex-none flex justify-center items-center gap-2 px-4 py-2 border border-surface-variant rounded-lg text-sm text-on-surface hover:bg-surface-container-low transition-colors">
                <Download className="w-4 h-4" /> Xuất
             </button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-low/30">
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">Quản trị viên</th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">Vai trò</th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">Phòng ban</th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">Đăng nhập lần cuối</th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant">Trạng thái</th>
                <th className="py-3 px-6 text-xs font-semibold text-on-surface-variant text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {admins.map((admin, i) => (
                <tr key={i} className="hover:bg-surface-container-lowest/50 transition-colors">
                  <td className="py-4 px-6 flex items-center gap-3">
                    {admin.avatar ? (
                      <img src={admin.avatar} alt={admin.name} className="w-10 h-10 rounded-full object-cover" />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center font-bold text-sm">
                        {admin.initials}
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-semibold text-on-surface">{admin.name}</p>
                      <p className="text-xs text-outline font-medium">{admin.email}</p>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm text-on-surface font-medium">{admin.role}</td>
                  <td className="py-4 px-6 text-sm text-on-surface">{admin.department}</td>
                  <td className={`py-4 px-6 text-sm ${admin.lastLogin === 'Chưa từng' ? 'italic text-outline' : 'text-on-surface'}`}>{admin.lastLogin}</td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${admin.color}`}>
                      {admin.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button className="text-outline hover:text-on-surface p-1 rounded hover:bg-surface-container-low transition-colors">
                       ...
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
