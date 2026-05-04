import { BarChart3, CheckCircle2, ClipboardList, Edit, Eye, Filter, MoreVertical, Plus } from "lucide-react";

export function Exams() {
  const exams = [
    { title: "Advanced Calculus Midterm", subject: "MATH-301", date: "15 thg 11, 2023 • 09:00 SA", status: "Đã xuất bản", statusColor: "text-primary bg-primary/10" },
    { title: "Modern European History Final", subject: "HIST-420", date: "02 thg 12, 2023 • 14:00 CH", status: "Bản nháp", statusColor: "text-outline bg-surface-variant" },
    { title: "Intro to Physics Quiz 4", subject: "PHYS-101", date: "28 thg 10, 2023 • 10:00 SA", status: "Hoàn thành", statusColor: "text-[#10B981] bg-[#10B981]/10" },
    { title: "Organic Chemistry Lab Safety", subject: "CHEM-205", date: "05 thg 11, 2023 • 08:30 SA", status: "Đã xuất bản", statusColor: "text-primary bg-primary/10" },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Bài thi</h1>
          
        </div>
        <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
          <Plus className="w-4 h-4" /> Tạo Bài thi
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <p className="text-sm font-medium text-outline">Hiệu suất Trung bình</p>
             <div className="w-8 h-8 rounded bg-primary-container text-on-primary-container flex items-center justify-center">
                <BarChart3 className="w-4 h-4" />
             </div>
          </div>
          <div className="w-full">
            <div className="flex items-baseline gap-3 mb-3">
               <p className="text-3xl font-bold text-on-surface">78.4%</p>
               <p className="text-xs font-semibold text-primary flex items-center gap-1">↑ 2.1%</p>
            </div>
            <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden flex">
               <div className="h-full bg-primary" style={{ width: '78.4%' }}></div>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <p className="text-sm font-medium text-outline">Tỷ lệ Hoàn thành Chung</p>
             <div className="w-8 h-8 rounded bg-green-100 text-green-700 flex items-center justify-center">
                <CheckCircle2 className="w-4 h-4" />
             </div>
          </div>
          <div className="w-full">
            <div className="flex items-baseline gap-3 mb-3">
               <p className="text-3xl font-bold text-on-surface">94.2%</p>
               <p className="text-xs text-outline">so với học kỳ trước</p>
            </div>
            <div className="w-full h-2 bg-surface-container-highest rounded-full overflow-hidden flex">
               <div className="h-full bg-primary" style={{ width: '94.2%' }}></div>
            </div>
          </div>
        </div>

        <div className="bg-surface-container-lowest rounded-xl p-5 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col justify-between items-start gap-4">
          <div className="flex w-full justify-between items-start">
             <p className="text-sm font-medium text-outline">Bài kiểm tra Đang hoạt động</p>
             <div className="w-8 h-8 rounded bg-secondary-container text-on-secondary-container flex items-center justify-center">
                <ClipboardList className="w-4 h-4" />
             </div>
          </div>
          <div className="w-full">
            <div className="flex items-baseline gap-3 mb-3">
               <p className="text-3xl font-bold text-on-surface">12</p>
               <p className="text-xs text-outline">Hiện đang diễn ra</p>
            </div>
            <div className="w-full h-2 rounded-full flex gap-1">
               <div className="h-full bg-primary rounded-full flex-1"></div>
               <div className="h-full bg-primary rounded-full flex-1"></div>
               <div className="h-full bg-surface-container-highest rounded-full flex-1"></div>
               <div className="h-full bg-surface-container-highest rounded-full flex-1"></div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] border border-surface-variant overflow-hidden">
        <div className="p-5 border-b border-surface-variant flex justify-between items-center bg-surface-container-lowest">
          <h3 className="text-lg font-bold text-on-surface">Bài thi Sắp tới & Gần đây</h3>
          <div className="flex items-center gap-3">
             <button className="text-outline hover:text-on-surface transition-colors p-1"><Filter className="w-5 h-5"/></button>
             <button className="text-outline hover:text-on-surface transition-colors p-1"><MoreVertical className="w-5 h-5"/></button>
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="border-b border-surface-variant bg-surface-container-lowest text-outline">
                <th className="py-4 px-6 text-xs font-semibold">Tên Bài thi</th>
                <th className="py-4 px-6 text-xs font-semibold">Môn học / Khóa học</th>
                <th className="py-4 px-6 text-xs font-semibold">Ngày dự kiến</th>
                <th className="py-4 px-6 text-xs font-semibold">Trạng thái</th>
                <th className="py-4 px-6 text-xs font-semibold text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-variant">
              {exams.map((exam, i) => (
                <tr key={i} className="hover:bg-surface-container-low/50 transition-colors bg-surface-container-lowest">
                  <td className="py-4 px-6 text-sm font-medium text-primary cursor-pointer hover:underline">{exam.title}</td>
                  <td className="py-4 px-6 text-sm text-outline font-medium">{exam.subject}</td>
                  <td className="py-4 px-6 text-sm text-on-surface font-medium">{exam.date}</td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${exam.statusColor}`}>
                      {exam.status === 'Đã xuất bản' && <CheckCircle2 className="w-3 h-3" />}
                      {exam.status === 'Bản nháp' && <Edit className="w-3 h-3" />}
                      {exam.status === 'Hoàn thành' && <CheckCircle2 className="w-3 h-3" />}
                      {exam.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-right flex justify-end gap-3">
                    <button className="text-outline hover:text-primary transition-colors"><Edit className="w-4 h-4"/></button>
                    {exam.status === 'Hoàn thành' ? (
                       <button className="text-outline hover:text-primary transition-colors"><BarChart3 className="w-4 h-4"/></button>
                    ) : (
                       <button className="text-outline hover:text-primary transition-colors"><Eye className="w-4 h-4"/></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination placeholder */}
        <div className="p-4 border-t border-surface-variant flex items-center justify-between text-sm text-outline">
           <p>Đang hiển thị 1 đến 4 trong số 24 bài thi</p>
           <div className="flex gap-2 items-center">
              <button className="px-2 py-1 hover:text-on-surface transition-colors">Trước</button>
              <button className="w-7 h-7 rounded bg-primary-container text-primary font-bold">1</button>
              <button className="w-7 h-7 rounded hover:bg-surface-container-low transition-colors">2</button>
              <button className="w-7 h-7 rounded hover:bg-surface-container-low transition-colors">3</button>
              <button className="px-2 py-1 hover:text-on-surface transition-colors">Sau</button>
           </div>
        </div>
      </div>
    </div>
  );
}
