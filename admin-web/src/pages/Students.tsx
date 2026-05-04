import { Download, Plus, Search, Users, UserPlus, UserCheck, UserMinus, TrendingUp, TrendingDown } from "lucide-react";

export function Students() {
  const students = [
    { id: "STU-84920", name: "Sarah Jenkins", email: "s.jenkins@student.educore.edu", grade: "A-", date: "01 thg 9 2023", status: "Đã ghi danh", avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop" },
    { id: "STU-84921", name: "Michael Chen", email: "m.chen@student.educore.edu", grade: "B+", date: "01 thg 9 2023", status: "Đã ghi danh", avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop" },
    { id: "STU-84922", name: "Aisha Rahman", email: "a.rahman@student.educore.edu", grade: "A", date: "15 thg 1 2024", status: "Đã ghi danh", initials: "AR", bg: "bg-secondary-container text-on-secondary-container" },
    { id: "STU-84923", name: "David Kim", email: "d.kim@student.educore.edu", grade: "C", date: "01 thg 9 2023", status: "Nghỉ phép", avatar: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&h=100&fit=crop" },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-xl font-semibold text-on-surface">Danh sách Học sinh</h1>
          
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 border border-primary text-primary rounded-lg text-sm font-medium hover:bg-primary/5 transition-colors flex items-center gap-2">
            <Download className="w-4 h-4" /> Xuất
          </button>
          <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
            <Plus className="w-4 h-4" /> Thêm Học sinh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center text-on-primary-fixed">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Tổng Học sinh</p>
              <p className="text-2xl font-semibold text-on-surface">2,451</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+12.5%</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-secondary-fixed flex items-center justify-center text-on-secondary-fixed">
              <UserPlus className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Học sinh mới</p>
              <p className="text-2xl font-semibold text-on-surface">350</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+5.1%</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#10B981]/10 flex items-center justify-center text-[#10B981]">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Đang hoạt động</p>
              <p className="text-2xl font-semibold text-on-surface">2,100</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#10B981] bg-[#10B981]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingUp className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">+8.2%</span>
          </div>
        </div>
        <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] flex items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-[#EF4444]/10 flex items-center justify-center text-[#EF4444]">
              <UserMinus className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm text-on-surface-variant">Bị khóa/đình chỉ</p>
              <p className="text-2xl font-semibold text-on-surface">12</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-[#EF4444] bg-[#EF4444]/10 px-2 py-1 rounded-md shrink-0">
            <TrendingDown className="w-3 h-3" strokeWidth={2.5} />
            <span className="text-xs font-semibold tracking-wide">-2.0%</span>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] flex flex-col overflow-hidden">
        <div className="p-4 border-b border-outline-variant bg-surface-container-lowest flex justify-between items-center gap-4">
          <div className="relative w-full max-w-md">
            <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Tìm kiếm học sinh theo tên hoặc ID..."
              className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-on-surface-variant hidden md:block">Bộ lọc theo:</span>
            <select className="bg-surface-container-low border border-outline-variant text-on-surface text-sm py-2 px-3 pl-4 pr-8 rounded-md focus:outline-none focus:border-primary">
              <option>Tất cả Hạng</option>
              <option>Hạng A</option>
              <option>Hạng B</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low/50 border-b border-surface-variant">
                <th className="py-3 px-4 w-12 text-center"><input type="checkbox" className="rounded text-primary focus:ring-primary" /></th>
                <th className="py-3 px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">Học sinh</th>
                <th className="py-3 px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">Mã số</th>
                <th className="py-3 px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">Hạng</th>
                <th className="py-3 px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">Ngày ghi danh</th>
                <th className="py-3 px-4 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider text-right pr-6">Trạng thái</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/50 flex-1">
              {students.map((student, i) => (
                <tr key={i} className="hover:bg-surface-container-low/30 transition-colors">
                  <td className="py-3 px-4 text-center"><input type="checkbox" className="rounded text-primary focus:ring-primary" /></td>
                  <td className="py-3 px-4 flex items-center gap-3">
                    {student.avatar ? (
                      <img src={student.avatar} alt={student.name} className="w-10 h-10 rounded-full object-cover border border-outline-variant/30" />
                    ) : (
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border border-outline-variant/30 ${student.bg}`}>
                        {student.initials}
                      </div>
                    )}
                    <div>
                      <p className="font-medium text-sm text-on-surface">{student.name}</p>
                      <p className="text-xs text-on-surface-variant">{student.email}</p>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">{student.id}</td>
                  <td className="py-3 px-4 text-sm font-medium text-on-surface">{student.grade}</td>
                  <td className="py-3 px-4 text-sm text-on-surface-variant">{student.date}</td>
                  <td className="py-3 px-4 text-right pr-6">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider uppercase
                      ${student.status === 'Đã ghi danh' ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-surface-variant text-on-surface-variant'}
                    `}>
                      {student.status}
                    </span>
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
