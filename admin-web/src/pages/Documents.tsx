import { FileAudio, FileImage, FileSpreadsheet, FileText, Filter, Folder, FolderClosed, Grid, LayoutList, Search, UploadCloud } from "lucide-react";

export function Documents() {
  const directories = [
    { name: "Chính sách Thể chế", active: true, children: ["Hướng dẫn Nhân sự", "Bảo mật CNTT"] },
    { name: "Khung Chương trình học", active: false },
    { name: "Tài sản Tiếp thị", active: false },
    { name: "Báo cáo Tài chính", active: false },
  ];

  const files = [
    { name: "Employee_Handbook_2024.pdf", type: "PDF Document", icon: FileText, iconColor: "text-red-500", size: "2.4 MB", date: "24 thg 10, 2023", permissions: "Tất cả nhân viên" },
    { name: "Q3_Performance_Review_Template.docx", type: "Word Document", icon: FileText, iconColor: "text-blue-500", size: "845 KB", date: "20 thg 10, 2023", permissions: "Chỉ Quản lý" },
    { name: "Annual_Budget_Draft_v2.xlsx", type: "Excel Spreadsheet", icon: FileSpreadsheet, iconColor: "text-green-500", size: "4.2 MB", date: "18 thg 10, 2023", permissions: "Hạn chế" },
    { name: "Campus_Map_HighRes.png", type: "Image", icon: FileImage, iconColor: "text-yellow-600", size: "8.1 MB", date: "15 thg 10, 2023", permissions: "Công khai" },
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6 h-[calc(100vh-4rem)]">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shrink-0">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Quản lý Tài liệu</h1> 
        </div>
        <button className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 shadow-sm">
          <UploadCloud className="w-4 h-4" /> Tải lên Tệp
        </button>
      </div>

      <div className="flex flex-col md:flex-row gap-6 flex-1 min-h-0">
        {/* Left Sidebar - Directories */}
        <div className="w-full md:w-64 flex flex-col shrink-0">
          <div className="bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] border border-surface-variant flex-1 overflow-y-auto">
             <div className="p-4 border-b border-surface-variant flex justify-between items-center bg-surface-container-lowest">
                <h3 className="font-bold text-on-surface">Thư mục</h3>
                <button className="text-outline hover:text-on-surface"><Folder className="w-4 h-4"/></button>
             </div>
             <div className="p-2 space-y-1">
                {directories.map((dir, i) => (
                   <div key={i}>
                      <button className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${dir.active ? 'bg-primary/10 text-primary' : 'text-on-surface hover:bg-surface-container-low'}`}>
                         <FolderClosed className={`w-4 h-4 ${dir.active ? 'text-primary' : 'text-outline'}`} />
                         {dir.name}
                      </button>
                      {dir.children && (
                         <div className="ml-5 mt-1 space-y-1 relative before:content-[''] before:absolute before:left-[11px] before:top-0 before:bottom-3 before:w-px before:bg-surface-dim">
                            {dir.children.map((child, j) => (
                               <button key={j} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-outline hover:text-on-surface hover:bg-surface-container-low transition-colors relative">
                                  <div className="absolute left-[-10px] top-1/2 w-[10px] h-px bg-surface-dim"></div>
                                  <FolderClosed className="w-4 h-4" />
                                  {child}
                               </button>
                            ))}
                         </div>
                      )}
                   </div>
                ))}
             </div>
          </div>
        </div>

        {/* Right Content - Files */}
        <div className="flex-1 bg-surface-container-lowest rounded-xl shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col min-h-0 overflow-hidden">
           <div className="p-4 border-b border-surface-variant flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-surface-container-lowest">
              <div className="flex items-center gap-2 text-sm">
                 <span className="font-bold text-on-surface">Chính sách Thể chế</span>
                 <span className="text-outline">/</span>
                 <span className="text-outline">Tất cả Tệp</span>
              </div>
              <div className="flex items-center gap-3 w-full sm:w-auto">
                 <div className="relative flex-1 sm:w-64">
                   <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                   <input
                     type="text"
                     placeholder="Tìm kiếm tệp..."
                     className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                   />
                 </div>
                 <button className="p-2 border border-outline-variant rounded-md text-outline hover:bg-surface-container-low transition-colors">
                    <Filter className="w-4 h-4" />
                 </button>
                 <div className="flex rounded-md p-1 bg-surface-container-low">
                    <button className="p-1.5 bg-surface-container-lowest shadow-sm rounded text-primary"><LayoutList className="w-4 h-4"/></button>
                    <button className="p-1.5 text-outline hover:text-on-surface"><Grid className="w-4 h-4"/></button>
                 </div>
              </div>
           </div>

           <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                 <thead className="bg-surface-container-lowest sticky top-0 z-10 border-b border-surface-variant">
                    <tr>
                       <th className="py-3 px-4 w-12 text-center"><input type="checkbox" className="rounded text-primary" /></th>
                       <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Tên</th>
                       <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Kích thước</th>
                       <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Sửa đổi</th>
                       <th className="py-3 px-4 text-xs font-bold text-on-surface uppercase tracking-wider">Quyền</th>
                    </tr>
                 </thead>
                 <tbody className="divide-y divide-surface-variant">
                    {files.map((file, i) => (
                       <tr key={i} className="hover:bg-surface-container-low/50 transition-colors cursor-pointer">
                          <td className="py-3 px-4 text-center"><input type="checkbox" className="rounded text-primary" /></td>
                          <td className="py-4 px-4 flex items-center gap-3">
                             <div className={`w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center ${file.iconColor}`}>
                                <file.icon className="w-5 h-5"/>
                             </div>
                             <div className="flex flex-col gap-0.5">
                                <p className="text-sm font-semibold text-on-surface leading-tight">{file.name}</p>
                                <p className="text-xs text-outline">{file.type}</p>
                             </div>
                          </td>
                          <td className="py-3 px-4 text-sm text-on-surface">{file.size}</td>
                          <td className="py-3 px-4 text-sm text-on-surface">{file.date}</td>
                          <td className="py-3 px-4">
                             <span className="inline-block px-3 py-1 bg-surface-container-low text-on-surface text-xs font-bold rounded-full">
                                {file.permissions}
                             </span>
                          </td>
                       </tr>
                    ))}
                 </tbody>
              </table>
           </div>
           
           <div className="p-4 border-t border-surface-variant flex items-center justify-between text-sm text-outline bg-surface-container-lowest">
              <p>Đang hiển thị 1 đến 4 trong số 24 tệp</p>
              <div className="flex gap-2 items-center">
                 <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-low transition-colors">&lt;</button>
                 <button className="w-7 h-7 rounded bg-primary text-on-primary font-bold">1</button>
                 <button className="w-7 h-7 rounded hover:bg-surface-container-low transition-colors">2</button>
                 <button className="w-7 h-7 rounded hover:bg-surface-container-low transition-colors">3</button>
                 <button className="w-7 h-7 flex items-center justify-center rounded hover:bg-surface-container-low transition-colors">&gt;</button>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
