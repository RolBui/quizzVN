import { Download, Plus, Search, MoreVertical, Users, UserCheck, FileText, Layout, TrendingUp, TrendingDown } from "lucide-react";

export function Teachers() {
  const teachers = [
    {
      id: "TCH-2045",
      name: "Sarah Jenkins",
      role: "Giáo viên cấp cao",
      department: "Toán học",
      email: "s.jenkins@educore.edu",
      status: "Hoạt động",
      avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=100&h=100&fit=crop"
    },
    {
      id: "TCH-1092",
      name: "Michael Chang",
      role: "Trưởng bộ môn",
      department: "Khoa học",
      email: "m.chang@educore.edu",
      status: "Hoạt động",
      avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop"
    },
    {
      id: "TCH-3105",
      name: "Emily Roberts",
      role: "Giáo viên",
      department: "Lịch sử",
      email: "e.roberts@educore.edu",
      status: "Nghỉ phép",
      avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop"
    },
    {
      id: "TCH-4022",
      name: "David Palmer",
      role: "Giáo viên",
      department: "Văn học Anh",
      email: "d.palmer@educore.edu",
      status: "Ngừng hoạt động",
      initials: "DP",
      avatar: ""
    },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6 h-full">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-semibold text-on-surface">Danh sách Giáo viên</h1>
          
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-surface border border-primary text-primary rounded-lg text-sm font-medium hover:bg-primary/5 transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" /> Xuất dữ liệu
          </button>
          <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
            <Plus className="w-4 h-4" /> Thêm Giáo viên
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Tổng số Giáo viên</p>
              <p className="text-2xl font-semibold text-on-surface">142</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+4.5%</span>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#10B981]/10 flex items-center justify-center text-[#10B981]">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Đang hoạt động</p>
              <p className="text-2xl font-semibold text-on-surface">138</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+2.1%</span>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed">
              <FileText className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Tổng đề thi đã tạo</p>
              <p className="text-2xl font-semibold text-on-surface">856</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+12.4%</span>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#F59E0B]/10 flex items-center justify-center text-[#F59E0B]">
              <Layout className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Tổng Lớp</p>
              <p className="text-2xl font-semibold text-on-surface">245</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+5.2%</span>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="flex gap-4 w-full md:w-auto">
          <select className="bg-surface-container-low border border-surface-variant text-on-surface text-sm py-2 px-3 rounded-lg focus:ring-1 focus:ring-primary outline-none">
            <option>Tất cả phòng ban</option>
            <option>Toán học</option>
            <option>Khoa học</option>
          </select>
          <select className="bg-surface-container-low border border-surface-variant text-on-surface text-sm py-2 px-3 rounded-lg focus:ring-1 focus:ring-primary outline-none">
            <option>Tất cả trạng thái</option>
            <option>Hoạt động</option>
            <option>Ngừng hoạt động</option>
          </select>
        </div>
        <div className="relative w-full md:w-72">
          <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Tìm kiếm theo tên, ID hoặc email..."
            className="w-full bg-surface-container-low rounded-lg pl-9 pr-3 py-2 text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none placeholder:text-outline"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] overflow-hidden flex-1">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/50 border-b border-surface-variant">
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider">Giáo viên</th>
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider">ID</th>
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider">Phòng ban</th>
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider">Liên hệ</th>
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider">Trạng thái</th>
                <th className="py-4 px-6 text-[11px] font-bold text-outline uppercase tracking-wider text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {teachers.map((teacher, i) => (
                <tr key={i} className="hover:bg-surface-container-low/50 transition-colors">
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      {teacher.avatar ? (
                        <img src={teacher.avatar} alt={teacher.name} className="w-10 h-10 rounded-full object-cover" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-primary-fixed-dim text-on-primary-fixed flex items-center justify-center font-semibold text-sm">
                          {teacher.initials}
                        </div>
                      )}
                      <div>
                        <p className="font-medium text-on-surface text-sm">{teacher.name}</p>
                        <p className="text-xs text-outline">{teacher.role}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-sm font-mono text-on-surface">{teacher.id}</td>
                  <td className="py-4 px-6 text-sm text-on-surface">{teacher.department}</td>
                  <td className="py-4 px-6 text-sm text-outline">{teacher.email}</td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
                      ${teacher.status === 'Hoạt động' ? 'bg-[#10B981]/10 text-[#10B981]' : ''}
                      ${teacher.status === 'Nghỉ phép' ? 'bg-[#F59E0B]/10 text-[#F59E0B]' : ''}
                      ${teacher.status === 'Ngừng hoạt động' ? 'bg-[#EF4444]/10 text-[#EF4444]' : ''}
                    `}>
                      {teacher.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right">
                    <button className="text-outline hover:text-primary transition-colors">
                      <MoreVertical className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="p-4 border-t border-surface-variant flex items-center justify-between bg-surface-container-lowest">
          <p className="text-sm text-outline">
            Đang hiển thị <span className="font-medium text-on-surface">1</span> tới <span className="font-medium text-on-surface">4</span> trong số <span className="font-medium text-on-surface">42</span> giáo viên
          </p>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 border border-surface-variant rounded-md text-sm text-outline hover:bg-surface-container-low transition-colors disabled:opacity-50" disabled>Trước</button>
            <button className="px-3 py-1.5 bg-primary-container text-on-primary-container rounded-md text-sm font-medium">1</button>
            <button className="px-3 py-1.5 hover:bg-surface-container-low rounded-md text-sm text-outline transition-colors">2</button>
            <button className="px-3 py-1.5 border border-surface-variant rounded-md text-sm text-on-surface hover:bg-surface-container-low transition-colors">Sau</button>
          </div>
        </div>
      </div>
    </div>
  );
}
