import { Edit, FileText, MoreVertical, Paperclip, Phone, Search, Send, Video } from "lucide-react";

export function Chat() {
  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left Sidebar - Chat List */}
      <div className="w-80 border-r border-surface-variant flex flex-col bg-surface-container-lowest shrink-0">
         <div className="p-4 border-b border-surface-variant flex flex-col gap-4">
            <div className="flex justify-between items-center">
               <h2 className="text-xl font-bold text-on-surface">Tin nhắn</h2>
               <button className="text-primary hover:bg-primary/10 p-1.5 rounded-lg transition-colors"><Edit className="w-5 h-5"/></button>
            </div>
            <div className="relative">
               <Search className="w-4 h-4 text-outline absolute left-3 top-1/2 -translate-y-1/2" />
               <input
                  type="text"
                  placeholder="Tìm kiếm cuộc trò chuyện..."
                  className="w-full pl-9 pr-4 py-2 bg-surface-container-low rounded-lg text-sm text-on-surface focus:ring-1 focus:ring-primary outline-none"
               />
            </div>
         </div>
         <div className="flex-1 overflow-y-auto">
            {/* Active Chat */}
            <div className="flex gap-3 p-4 cursor-pointer relative border-l-4 border-primary bg-primary/5">
                <div className="relative">
                   <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop" alt="Sarah Jenkins" className="w-12 h-12 rounded-full object-cover" />
                   <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-surface-container-lowest rounded-full"></div>
                </div>
                <div className="flex-1 min-w-0">
                   <div className="flex justify-between items-baseline mb-1">
                      <p className="font-semibold text-on-surface truncate">Sarah Jenkins</p>
                      <p className="text-xs text-outline shrink-0 ml-2">10:42 SA</p>
                   </div>
                   <p className="text-sm text-on-surface truncate font-medium">Cảm ơn thầy đã tải lên mẫu mới...</p>
                </div>
            </div>
            {/* Other Chat */}
            <div className="flex gap-3 p-4 cursor-pointer hover:bg-surface-container-low transition-colors border-l-4 border-transparent">
                <div className="w-12 h-12 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center font-bold text-lg shrink-0">
                   MD
                </div>
                <div className="flex-1 min-w-0">
                   <div className="flex justify-between items-baseline mb-1">
                      <p className="font-semibold text-on-surface truncate">Math Dept Group</p>
                      <p className="text-xs text-outline shrink-0 ml-2">Hôm qua</p>
                   </div>
                   <p className="text-sm text-outline truncate">Dr. Evans: Việc chấm điểm giữa kỳ...</p>
                </div>
                <div className="w-5 h-5 rounded-full bg-primary text-on-primary flex items-center justify-center text-[10px] font-bold mt-6">
                   2
                </div>
            </div>
         </div>
      </div>

      {/* Middle - Chat History */}
      <div className="flex-1 flex flex-col bg-surface-container-lowest/50 min-w-0">
         {/* Header */}
         <div className="h-16 px-6 border-b border-surface-variant flex justify-between items-center bg-surface-container-lowest shrink-0">
            <div className="flex flex-col">
               <h3 className="font-bold text-on-surface flex items-center gap-2">
                  <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop" className="w-8 h-8 rounded-full sm:hidden"/>
                  Sarah Jenkins
               </h3>
              <p className="text-xs text-[#10B981] font-medium flex items-center gap-1.5">Trực tuyến</p>
            </div>
            <div className="flex items-center gap-4">
               <button className="text-outline hover:text-on-surface"><Phone className="w-5 h-5"/></button>
               <button className="text-outline hover:text-on-surface"><Video className="w-5 h-5"/></button>
               <button className="text-outline hover:text-on-surface"><MoreVertical className="w-5 h-5"/></button>
            </div>
         </div>

         {/* Messages */}
         <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
            <div className="text-center font-medium text-xs text-outline tracking-wider">HÔM NAY, 10:30 SA</div>
            
            {/* Received Message */}
            <div className="flex justify-start">
               <div className="bg-surface-container-low text-on-surface px-5 py-3 rounded-2xl rounded-tl-sm max-w-[75%] shadow-sm">
                  <p className="text-sm leading-relaxed">Chào Giáo sư, em muốn hỏi xem đề cương mới cho môn Giải tích Nâng cao đã được tải lên chưa ạ?</p>
               </div>
            </div>

            {/* Sent Message */}
            <div className="flex justify-end flex-col items-end gap-1">
               <div className="bg-[#2E3C8A] text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[75%] shadow-sm">
                  <p className="text-sm leading-relaxed">Chào Sarah. Có, tôi vừa tải nó lên phần Tài liệu vài phút trước.</p>
               </div>
               <p className="text-xs text-outline flex items-center gap-1">10:35 SA <span className="text-primary tracking-tighter">✓✓</span></p>
            </div>

            {/* Received Message */}
            <div className="flex justify-start flex-col items-start gap-1">
               <div className="bg-surface-container-low text-on-surface px-5 py-3 rounded-2xl rounded-tl-sm max-w-[75%] shadow-sm">
                  <p className="text-sm leading-relaxed">Tuyệt vời, em đã thấy rồi! Cảm ơn thầy đã tải lên đề cương mới!</p>
               </div>
               <p className="text-xs text-outline">10:42 SA</p>
            </div>
         </div>

         {/* Input */}
         <div className="p-4 bg-surface-container-lowest border-t border-surface-variant shrink-0">
            <div className="flex items-center gap-2">
               <div className="flex-1 bg-surface-container-low rounded-xl border border-outline-variant flex items-center pl-4 pr-2 py-2">
                  <button className="text-outline hover:text-on-surface mr-3"><Paperclip className="w-5 h-5"/></button>
                  <input type="text" placeholder="Nhập tin nhắn..." className="flex-1 bg-transparent text-sm text-on-surface outline-none" />
               </div>
               <button className="w-12 h-12 rounded-xl bg-[#2E3C8A] text-white flex items-center justify-center hover:bg-[#2E3C8A]/90 transition-colors shrink-0 shadow-sm">
                  <Send className="w-5 h-5 ml-1"/>
               </button>
            </div>
         </div>
      </div>

      {/* Right Sidebar - Profile & Files */}
      <div className="w-72 border-l border-surface-variant bg-surface-container-lowest hidden lg:flex flex-col shrink-0">
         <div className="p-8 flex flex-col items-center border-b border-surface-variant">
            <img src="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=100&h=100&fit=crop" className="w-24 h-24 rounded-full object-cover mb-4" />
            <h3 className="font-bold text-lg text-on-surface text-center">Sarah Jenkins</h3>
            <p className="text-sm text-outline mt-1 text-center">Học sinh năm 3 • Lớp '25</p>
            <button className="w-full mt-6 py-2 border border-[#2E3C8A] text-[#2E3C8A] rounded-lg text-sm font-semibold hover:bg-[#2E3C8A]/5 transition-colors">
               Hồ sơ
            </button>
         </div>

         <div className="p-6 flex-1 overflow-y-auto">
            <h4 className="text-xs font-bold text-outline uppercase tracking-wider mb-4">Tệp & Phương tiện Đã chia sẻ</h4>
            <div className="flex flex-col gap-3">
               <div className="p-3 border border-surface-variant rounded-xl flex items-center gap-3 cursor-pointer hover:bg-surface-container-low transition-colors shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-red-100 text-red-600 flex items-center justify-center shrink-0">
                     <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                     <p className="text-sm font-semibold text-on-surface truncate">Calculus_Syllabus_F...</p>
                     <p className="text-xs text-outline mt-0.5">1.2 MB • Hôm nay</p>
                  </div>
               </div>
               
               <div className="p-3 border border-surface-variant rounded-xl flex items-center gap-3 cursor-pointer hover:bg-surface-container-low transition-colors shadow-sm">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                     <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                     <p className="text-sm font-semibold text-on-surface truncate">Assignment_1_Draft....</p>
                     <p className="text-xs text-outline mt-0.5">245 KB • 12 thg 10</p>
                  </div>
               </div>
            </div>
         </div>
      </div>
    </div>
  );
}
