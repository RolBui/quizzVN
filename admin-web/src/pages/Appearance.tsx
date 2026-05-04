import { Calendar, Image as ImageIcon, Link, UploadCloud, Users, LayoutTemplate } from "lucide-react";

export function Appearance() {
  const banners = [
    {
       title: "Đăng ký Học kỳ Mùa thu",
       audience: "Tất cả học sinh",
       dates: "01 thg 9 - 30 thg 9",
       status: "ĐANG HOẠT ĐỘNG",
       statusColor: "text-green-700 bg-green-100",
       image: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400&h=200&fit=crop"
    },
    {
       title: "Tính năng mới: Bảng trắng Tương tác",
       audience: "Chỉ dành cho giáo viên",
       dates: "15 thg 10 - 15 thg 11",
       status: "ĐANG HOẠT ĐỘNG",
       statusColor: "text-green-700 bg-green-100",
       image: "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400&h=200&fit=crop"
    },
    {
       title: "Bảo trì Kỳ nghỉ mùa Đông",
       audience: "Tất cả người dùng",
       dates: "24 thg 12 - 02 thg 1",
       status: "ĐÃ LÊN LỊCH",
       statusColor: "text-outline bg-surface-variant",
       image: "https://images.unsplash.com/photo-1481504281729-ea9bbd5135ec?w=400&h=200&fit=crop"
    }
  ];

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4 md:gap-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl md:text-xl font-bold text-on-surface">Tùy chỉnh Banner</h1>
          
        </div>
        <button className="px-4 py-2 bg-[#4C5B9E] text-white rounded-lg text-sm font-medium hover:bg-[#4C5B9E]/90 transition-colors flex items-center gap-2 shadow-sm">
          <UploadCloud className="w-4 h-4" /> Xuất bản Banner mới
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
         {/* Form Create */}
         <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col">
            <h2 className="text-lg font-bold text-on-surface flex items-center gap-2 mb-6">
               <ImageIcon className="w-5 h-5 text-[#4C5B9E]" /> Tạo Banner mới
            </h2>
            
            <div className="space-y-6">
               <div>
                  <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Hình ảnh Banner</label>
                  <div className="border-2 border-dashed border-outline-variant bg-surface-container-low/30 rounded-xl p-10 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-surface-container-low transition-colors">
                     <UploadCloud className="w-8 h-8 text-outline mb-4" />
                     <p className="text-sm font-semibold text-on-surface mb-1">Nhấp để tải lên hoặc kéo và thả</p>
                     <p className="text-xs text-outline">SVG, PNG, JPG hoặc GIF (tối đa 800x400px)</p>
                  </div>
               </div>

               <div>
                  <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">URL liên kết đích</label>
                  <div className="relative">
                     <Link className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                     <input type="text" placeholder="https://educore.lms/campaign" className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none" />
                  </div>
               </div>

               <div className="grid grid-cols-2 gap-4">
                  <div>
                     <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Ngày bắt đầu</label>
                     <div className="relative">
                        <Calendar className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="dd/mm/yyyy" className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none" />
                     </div>
                  </div>
                  <div>
                     <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Ngày kết thúc</label>
                     <div className="relative">
                        <Calendar className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                        <input type="text" placeholder="dd/mm/yyyy" className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none" />
                     </div>
                  </div>
               </div>

               <div>
                  <label className="block text-[11px] font-bold text-outline uppercase tracking-wider mb-2">Đối tượng mục tiêu</label>
                  <div className="relative">
                     <Users className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
                     <select className="w-full pl-9 pr-4 py-2 bg-surface-container-low border border-outline-variant rounded-md text-sm text-on-surface focus:border-primary focus:ring-1 focus:ring-[#4C5B9E] outline-none appearance-none">
                        <option>Tất cả người dùng</option>
                        <option>Tất cả học viên</option>
                        <option>Tất cả giáo viên</option>
                     </select>
                     <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-outline"><path d="m6 9 6 6 6-6"/></svg>
                     </div>
                  </div>
               </div>
            </div>
         </div>

         {/* List Active */}
         <div className="bg-surface-container-lowest rounded-xl p-6 shadow-[var(--shadow-level-1)] border border-surface-variant flex flex-col">
            <div className="flex justify-between items-center mb-6 pb-2 border-b border-surface-variant">
               <h2 className="text-lg font-bold text-on-surface flex items-center gap-2">
                  <LayoutTemplate className="w-5 h-5 text-[#4C5B9E]" />
                  Đang hoạt động & Đã lên lịch
               </h2>
               <div className="flex gap-2">
                  <span className="px-3 py-1 bg-surface-container-low text-on-surface-variant rounded-full text-[11px] font-semibold border border-surface-variant">3 Đang hoạt động</span>
                  <span className="px-3 py-1 bg-surface-container-low text-on-surface-variant rounded-full text-[11px] font-semibold border border-surface-variant">1 Đã lên lịch</span>
               </div>
            </div>

            <div className="space-y-4">
               {banners.map((banner, i) => (
                  <div key={i} className="flex flex-col sm:flex-row gap-4 p-4 border border-surface-variant rounded-xl shadow-sm hover:bg-surface-container-low/50 transition-colors">
                     <div className="relative w-full sm:w-48 h-28 shrink-0 rounded-lg overflow-hidden bg-surface-container">
                        <img src={banner.image} alt={banner.title} className="w-full h-full object-cover" />
                        <div className="absolute top-2 right-2">
                           <span className={`text-[9px] uppercase font-bold tracking-widest px-2 py-0.5 rounded-sm ${banner.statusColor}`}>
                              {banner.status}
                           </span>
                        </div>
                     </div>
                     <div className="flex flex-col justify-center gap-1.5">
                        <h3 className="font-bold text-on-surface leading-tight text-sm">{banner.title}</h3>
                        <div className="flex flex-col gap-2 mt-2">
                           <p className="text-sm text-outline flex items-center gap-2">
                              <Users className="w-4 h-4" /> {banner.audience}
                           </p>
                           <p className="text-sm text-outline flex items-center gap-2">
                              <Calendar className="w-4 h-4" /> {banner.dates}
                           </p>
                        </div>
                     </div>
                  </div>
               ))}
            </div>
         </div>
      </div>
    </div>
  );
}
