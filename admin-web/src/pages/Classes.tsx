import { Filter, Plus, Search, MoreVertical, Users, Calendar } from "lucide-react";

export function Classes() {
  const classes = [
    {
      id: 1,
      department: "Khoa Toán học",
      title: "Advanced Calculus 401",
      status: "ĐANG HOẠT ĐỘNG",
      statusColor: "text-green-600 bg-green-100",
      image: "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=600&q=80",
      instructor: {
        name: "TS. Eleanor Smith",
        role: "Trưởng Giáo sư",
        avatar: "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=100&h=100&fit=crop"
      },
      students: { current: 42, max: 50 },
      schedule: "T2, T4 10:00 Sáng"
    },
    {
      id: 2,
      department: "Khoa học Máy tính",
      title: "Data Structures & Algos",
      status: "ĐANG HOẠT ĐỘNG",
      statusColor: "text-green-600 bg-green-100",
      image: "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=600&q=80",
      instructor: {
        name: "GS. Michael Chen",
        role: "Giảng viên Cao cấp",
        avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop"
      },
      students: { current: 118, max: 120 },
      schedule: "T3, T5 2:00 Chiều"
    },
    {
      id: 3,
      department: "Thiết kế & Kiến trúc",
      title: "Modern Urban Planning",
      status: "SẮP TỚI",
      statusColor: "text-yellow-600 bg-yellow-100",
      image: "", // We can use empty for placeholder
      instructor: {
        name: "Chưa xác định",
        role: "Giảng viên thỉnh giảng",
        avatar: ""
      },
      students: { current: 0, max: 35 },
      schedule: "Bắt đầu ngày 1 tháng 9"
    }
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Lớp học</h1>
          
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <button className="flex-1 md:flex-none flex justify-center items-center gap-2 px-4 py-2 border border-surface-variant rounded-lg text-sm text-on-surface hover:bg-surface-container-low transition-colors">
            <Filter className="w-4 h-4" /> Bộ lọc
          </button>
          <button className="flex-1 md:flex-none px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex justify-center items-center gap-2 shadow-sm">
            <Plus className="w-4 h-4" /> Tạo Lớp mới
          </button>
        </div>
      </div>

      <div className="border-b border-surface-variant flex gap-6 mt-2">
         <button className="pb-3 text-sm font-semibold text-primary border-b-2 border-primary">Tất cả Lớp học</button>
         <button className="pb-3 text-sm font-medium text-outline hover:text-on-surface transition-colors">Chỉ hoạt động</button>
         <button className="pb-3 text-sm font-medium text-outline hover:text-on-surface transition-colors">Sắp tới</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-2">
        {classes.map((cls) => (
          <div key={cls.id} className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] border border-surface-variant overflow-hidden flex flex-col">
            <div className="h-32 bg-surface-container-low relative">
              {cls.image ? (
                <img src={cls.image} alt={cls.title} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-outline">
                  <div className="w-10 h-10">
                     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="5" r="3"/><line x1="12" y1="22" x2="12" y2="8"/><path d="M5 12H2a4 4 0 0 0 4 4h0a4 4 0 0 0 4-4h-2"/><path d="M15 12h-2a4 4 0 0 0 4 4h0a4 4 0 0 0 4-4h-3"/></svg>
                  </div>
                </div>
              )}
              <div className="absolute top-3 right-3">
                 <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded-md flex items-center gap-1 ${cls.statusColor}`}>
                    {cls.status}
                 </span>
              </div>
            </div>
            
            <div className="p-5 flex flex-col flex-1">
               <div className="flex justify-between items-start mb-2">
                  <p className="text-[10px] font-bold text-primary uppercase tracking-widest">{cls.department}</p>
                  <MoreVertical className="w-4 h-4 text-outline cursor-pointer" />
               </div>
               <h3 className="text-lg font-bold text-on-surface leading-tight mb-4">{cls.title}</h3>
               
               <div className="flex items-center gap-3 mb-6">
                  {cls.instructor.avatar ? (
                     <img src={cls.instructor.avatar} alt={cls.instructor.name} className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                     <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center text-outline">
                        <Users className="w-5 h-5"/>
                     </div>
                  )}
                  <div>
                     <p className="text-sm font-semibold text-on-surface">{cls.instructor.name}</p>
                     <p className="text-xs text-outline">{cls.instructor.role}</p>
                  </div>
               </div>

               <div className="mt-auto grid grid-cols-2 pt-4 border-t border-surface-variant gap-4">
                  <div>
                     <p className="text-xs font-semibold text-outline flex items-center gap-1.5 mb-1"><Users className="w-3.5 h-3.5"/> Học sinh</p>
                     <p className="text-xl font-bold text-on-surface leading-none">{cls.students.current} <span className="text-sm font-medium text-outline">/ {cls.students.max}</span></p>
                  </div>
                  <div>
                     <p className="text-xs font-semibold text-outline flex items-center gap-1.5 mb-1"><Calendar className="w-3.5 h-3.5"/> Lịch học</p>
                     <p className="text-sm font-medium text-on-surface leading-tight">{cls.schedule}</p>
                  </div>
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
